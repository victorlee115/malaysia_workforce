from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime

from malaysia_workforce.data_access import get_malaysia_profile, get_scheme_treatment, get_work_agreement
from malaysia_workforce.statutory.snapshot import parse_statutory_snapshot
from malaysia_workforce.utils import ensure_roles, select_for_update, stable_json, validate_date_range

PAY_ENGINE_VERSION = "MW-PAY-2026.3"


def _ensure_permission():
	ensure_roles("Malaysia Payroll User", "System Manager")


def _employee_scope(entry) -> set[str] | None:
	filters = {"company": entry.company, "status": "Active"}
	if entry.branch:
		filters["branch"] = entry.branch
	if entry.department:
		filters["department"] = entry.department
	if not entry.branch and not entry.department:
		return None
	return set(frappe.get_all("Employee", filters=filters, pluck="name", limit=100000))


def _work_records(entry, *, lock: bool = False):
	conditions = [
		"company=%s",
		"work_date BETWEEN %s AND %s",
		"docstatus=1",
		"status IN ('Approved','Automatically Verified','Payroll Generated')",
	]
	values: list = [entry.company, entry.start_date, entry.end_date]
	scope = _employee_scope(entry)
	if scope is not None:
		if not scope:
			return []
		conditions.append(f"employee IN ({', '.join(['%s'] * len(scope))})")
		values.extend(sorted(scope))
	query = f"""
		SELECT name, employee, gross_pay, status, pre_payroll_status,
			additional_salary_references, work_date, payroll_entry,
			calculation_snapshot, modified
		FROM `tabShift Work Record`
		WHERE {' AND '.join(conditions)}
		ORDER BY employee, work_date, name
	"""
	rows = (select_for_update if lock else frappe.db.sql)(
		query,
		values,
		as_dict=True,
	)
	return rows


def _source_hash(rows) -> str:
	payload = [
		{
			"name": row.name,
			"employee": row.employee,
			"work_date": str(row.work_date),
			"gross_pay": str(row.gross_pay or 0),
			"calculation_snapshot": row.calculation_snapshot or "",
		}
		for row in rows
	]
	return hashlib.sha256(stable_json(payload).encode()).hexdigest()


def _current_assignment(employee: str, company: str, on_date):
	rows = frappe.get_all(
		"Salary Structure Assignment",
		filters={"employee": employee, "company": company, "docstatus": 1, "from_date": ["<=", on_date]},
		fields=["name", "salary_structure", "from_date", "payroll_payable_account"],
		order_by="from_date desc, creation desc",
		limit=20,
	)
	return rows[0] if rows else None


def _validate_assignment(employee: str, entry) -> str | None:
	joining_date = frappe.db.get_value("Employee", employee, "date_of_joining")
	effective = getdate(joining_date) if joining_date and getdate(joining_date) > getdate(entry.start_date) else getdate(entry.start_date)
	assignment = _current_assignment(employee, entry.company, effective)
	if not assignment:
		return "no submitted Salary Structure Assignment"
	structure = frappe.db.get_value(
		"Salary Structure",
		assignment.salary_structure,
		["company", "payroll_frequency", "is_active", "docstatus"],
		as_dict=True,
	)
	if not structure or int(structure.docstatus or 0) != 1 or structure.is_active != "Yes":
		return f"Salary Structure {assignment.salary_structure} is not submitted and active"
	if structure.company != entry.company:
		return f"Salary Structure {assignment.salary_structure} belongs to another company"
	if structure.payroll_frequency and structure.payroll_frequency != entry.payroll_frequency:
		return f"Salary Structure {assignment.salary_structure} uses {structure.payroll_frequency}"
	return None


def _validate_entry(entry, rows) -> tuple[list[str], list[str]]:
	errors: list[str] = []
	warnings: list[str] = []
	validate_date_range(entry.start_date, entry.end_date, "Payroll Entry")
	company = frappe.get_cached_doc("Company", entry.company)
	if not company.custom_enable_malaysia_payroll:
		errors.append("Malaysia payroll is not enabled on the Company.")
	try:
		from malaysia_workforce.compliance.scope import assert_rule_review_current

		assert_rule_review_current(entry.company, entry.end_date)
	except (frappe.ValidationError, frappe.PermissionError) as exc:
		errors.append(str(exc))
	if not rows:
		errors.append("No submitted, approved Shift Work Records were found for this period.")
	for row in rows:
		if row.payroll_entry and row.payroll_entry != entry.name:
			errors.append(f"{row.name}: already reserved by Payroll Entry {row.payroll_entry}.")
		if Decimal(str(row.gross_pay or 0)) < 0:
			errors.append(f"{row.name}: gross pay cannot be negative.")
	for employee in sorted({row.employee for row in rows}):
		agreement = get_work_agreement(employee, entry.end_date)
		if not agreement:
			errors.append(f"{employee}: no effective Employee Work Agreement.")
		profile = get_malaysia_profile(employee)
		if not profile:
			errors.append(f"{employee}: no Malaysia Employee Profile.")
			continue
		assignment_error = _validate_assignment(employee, entry)
		if assignment_error:
			errors.append(f"{employee}: {assignment_error}.")
		for scheme, registration_field in (("EPF", "epf_number"), ("SOCSO", "socso_number"), ("EIS", "eis_number")):
			treatment, _, _ = get_scheme_treatment(employee, scheme, entry.end_date)
			if treatment == "Pending Review":
				errors.append(f"{employee}: {scheme} treatment is Pending Review.")
			elif treatment != "Not Applicable" and not profile.get(registration_field):
				errors.append(f"{employee}: {scheme} registration number is missing.")
		pcb_treatment, _, _ = get_scheme_treatment(employee, "PCB", entry.end_date)
		if pcb_treatment == "Pending Review":
			errors.append(f"{employee}: PCB treatment is Pending Review.")
		elif pcb_treatment != "Not Applicable" and not profile.income_tax_number:
			warnings.append(f"{employee}: income tax number is missing; LHDN validation may fail.")
	return errors, warnings


def _reserve(entry, rows) -> str:
	current_hash = _source_hash(rows)
	if entry.custom_malaysia_source_snapshot_hash and entry.custom_malaysia_source_snapshot_hash != current_hash:
		frappe.throw(_("The approved work-record source changed. Reset the draft Payroll Entry and revalidate."))
	for row in rows:
		if not row.payroll_entry:
			frappe.db.set_value(
				"Shift Work Record",
				row.name,
				{"payroll_entry": entry.name, "pre_payroll_status": row.pre_payroll_status or row.status},
				update_modified=False,
			)
	return current_hash


def _batch_key(entry_name: str, employee: str, component: str) -> str:
	return hashlib.sha256(f"{entry_name}|{employee}|{component}".encode()).hexdigest()


def _generate_additional_salaries(entry, rows) -> list[str]:
	settings = frappe.get_cached_doc("Malaysia Workforce Settings")
	component_map = {
		"Casual Ordinary Pay": settings.casual_ordinary_component,
		"Part-Time Additional Hours": settings.casual_additional_component,
		"Casual Overtime Pay": settings.casual_overtime_component,
		"Rest Day Pay": settings.rest_day_component,
		"Public Holiday Pay": settings.public_holiday_component,
	}
	aggregates = defaultdict(lambda: {"amount": Decimal("0"), "records": []})
	for row in rows:
		record = frappe.get_doc("Shift Work Record", row.name)
		if not record.pay_breakdown:
			frappe.throw(_("Shift Work Record {0} has no frozen pay breakdown.").format(record.name))
		for line in record.pay_breakdown:
			component = component_map.get(line.salary_component, line.salary_component)
			if not component or not frappe.db.exists("Salary Component", component):
				frappe.throw(_("Salary Component {0} is missing.").format(component or line.salary_component))
			key = (record.employee, component)
			aggregates[key]["amount"] += Decimal(str(line.amount or 0))
			aggregates[key]["records"].append(record.name)
	created = []
	by_employee = defaultdict(list)
	for (employee, component), data in sorted(aggregates.items()):
		key = _batch_key(entry.name, employee, component)
		existing = frappe.db.get_value(
			"Additional Salary",
			{"custom_source_batch_key": key, "docstatus": ["<", 2]},
			["name", "amount", "employee", "company", "salary_component", "payroll_date", "ref_doctype", "ref_docname"],
			as_dict=True,
		)
		expected = float(data["amount"])
		if existing:
			if (
				existing.employee != employee
				or existing.company != entry.company
				or existing.salary_component != component
				or getdate(existing.payroll_date) != getdate(entry.posting_date)
				or existing.ref_doctype != "Payroll Entry"
				or existing.ref_docname != entry.name
				or abs(float(existing.amount or 0) - expected) > 0.001
			):
				frappe.throw(_("Generated Additional Salary {0} no longer matches its frozen source.").format(existing.name))
			name = existing.name
		else:
			doc = frappe.new_doc("Additional Salary")
			doc.employee = employee
			doc.company = entry.company
			doc.salary_component = component
			doc.amount = expected
			doc.payroll_date = entry.posting_date
			doc.overwrite_salary_structure_amount = 0
			doc.ref_doctype = "Payroll Entry"
			doc.ref_docname = entry.name
			doc.custom_generated_by_malaysia_workforce = 1
			doc.custom_source_batch_key = key
			doc.custom_pay_calculation_version = PAY_ENGINE_VERSION
			doc.insert(ignore_permissions=True)
			name = doc.name
		created.append(name)
		by_employee[employee].append(name)
	for row in rows:
		frappe.db.set_value(
			"Shift Work Record",
			row.name,
			{
				"status": "Payroll Generated",
				"pre_payroll_status": row.pre_payroll_status or row.status,
				"payroll_entry": entry.name,
				"payroll_date": entry.posting_date,
				"additional_salary_references": "\n".join(sorted(by_employee[row.employee])),
			},
			update_modified=True,
		)
	return created


@frappe.whitelist(methods=["POST"])
def prepare_payroll_entry(payroll_entry: str) -> dict:
	"""Validate, reserve and prepare casual earnings on the standard Payroll Entry."""
	_ensure_permission()
	entry = frappe.get_doc("Payroll Entry", payroll_entry)
	entry.check_permission("write")
	if entry.docstatus != 0:
		frappe.throw(_("Prepare Malaysia inputs before submitting Payroll Entry."))
	select_for_update("SELECT name FROM `tabPayroll Entry` WHERE name=%s", (entry.name,))
	rows = _work_records(entry, lock=True)
	errors, warnings = _validate_entry(entry, rows)
	if errors:
		entry.custom_malaysia_enabled = 1
		entry.custom_malaysia_control_state = "Validation Failed"
		entry.custom_malaysia_work_record_reservation_status = "Not Reserved"
		entry.custom_malaysia_validation_errors = json.dumps({"errors": errors, "warnings": warnings}, indent=2)
		entry.save()
		return {"payroll_entry": entry.name, "status": "Validation Failed", "errors": errors, "warnings": warnings}
	source_hash = _reserve(entry, rows)
	additional_salaries = _generate_additional_salaries(entry, rows)
	expected = sorted({row.employee for row in rows})
	entry.fill_employee_details()
	entry.set("employees", [row for row in entry.employees if row.employee in expected])
	actual = sorted(row.employee for row in entry.employees)
	if actual != expected:
		missing = sorted(set(expected) - set(actual))
		frappe.throw(_("Payroll Entry could not include employees: {0}. Check Salary Structure Assignments.").format(", ".join(missing)))
	entry.number_of_employees = len(actual)
	entry.custom_malaysia_enabled = 1
	entry.custom_malaysia_control_state = "Validated"
	entry.custom_malaysia_work_record_reservation_status = "Reserved"
	entry.custom_malaysia_source_snapshot_hash = source_hash
	entry.custom_malaysia_validation_errors = json.dumps({"errors": [], "warnings": warnings}, indent=2)
	entry.custom_malaysia_processed_by = frappe.session.user
	entry.save()
	return {
		"payroll_entry": entry.name,
		"status": "Validated",
		"employee_count": len(actual),
		"additional_salaries": additional_salaries,
		"source_work_record_hash": source_hash,
		"warnings": warnings,
	}


def release_work_record_reservations(payroll_entry: str) -> int:
	_ensure_permission()
	entry = frappe.get_doc("Payroll Entry", payroll_entry)
	if entry.docstatus != 0:
		frappe.throw(_("Only a draft Payroll Entry can release work-record reservations."))
	if frappe.db.exists(
		"Additional Salary",
		{"ref_doctype": "Payroll Entry", "ref_docname": entry.name, "docstatus": ["<", 2]},
	):
		frappe.throw(_("Cancel generated Additional Salary records before resetting this Payroll Entry."))
	rows = frappe.get_all(
		"Shift Work Record",
		filters={"payroll_entry": entry.name},
		fields=["name", "pre_payroll_status", "additional_salary_references"],
		limit=100000,
	)
	for row in rows:
		if row.additional_salary_references:
			frappe.throw(_("Shift Work Record {0} still contains payroll references.").format(row.name))
		frappe.db.set_value(
			"Shift Work Record",
			row.name,
			{"status": row.pre_payroll_status or "Approved", "pre_payroll_status": "", "payroll_entry": "", "payroll_date": None},
			update_modified=True,
		)
	entry.db_set(
		{
			"custom_malaysia_source_snapshot_hash": "",
			"custom_malaysia_control_state": "Not Started",
			"custom_malaysia_work_record_reservation_status": "Released",
			"custom_malaysia_validation_errors": "",
		},
		update_modified=True,
	)
	return len(rows)


def _validated_company_account(account: str | None, company: str, label: str) -> str:
	if not account:
		frappe.throw(_("Configure {0} in Malaysia Workforce Settings.").format(label))
	row = frappe.db.get_value("Account", account, ["company", "is_group", "account_currency"], as_dict=True)
	if not row or row.company != company or row.is_group:
		frappe.throw(_("{0} must be a non-group Account belonging to {1}.").format(label, company))
	company_currency = frappe.db.get_value("Company", company, "default_currency")
	if row.account_currency and row.account_currency != company_currency:
		frappe.throw(_("{0} must use the Company's default currency.").format(label))
	return account


def employer_contribution_account_map(company: str) -> dict[str, tuple[str, str]]:
	settings = frappe.get_cached_doc("Malaysia Workforce Settings")
	return {
		"EPF": (_validated_company_account(settings.employer_epf_expense_account, company, "Employer EPF Expense Account"), _validated_company_account(settings.epf_payable_account, company, "EPF Payable Account")),
		"SOCSO": (_validated_company_account(settings.employer_socso_expense_account, company, "Employer SOCSO Expense Account"), _validated_company_account(settings.socso_payable_account, company, "SOCSO Payable Account")),
		"EIS": (_validated_company_account(settings.employer_eis_expense_account, company, "Employer EIS Expense Account"), _validated_company_account(settings.eis_payable_account, company, "EIS Payable Account")),
		"HRD Corp": (_validated_company_account(settings.employer_hrd_expense_account, company, "HRD Corp Levy Expense Account"), _validated_company_account(settings.hrd_payable_account, company, "HRD Corp Levy Payable Account")),
	}


def create_employer_contribution_journal(*, payroll_entry):
	_ensure_permission()
	entry = frappe.get_doc("Payroll Entry", payroll_entry) if isinstance(payroll_entry, str) else payroll_entry
	if entry.docstatus != 1:
		frappe.throw(_("Payroll Entry must be submitted before employer contributions are accrued."))
	if entry.custom_malaysia_employer_contribution_journal:
		existing = frappe.get_doc("Journal Entry", entry.custom_malaysia_employer_contribution_journal)
		if existing.docstatus < 2:
			return existing.name
	key = f"EMPLOYER-CONTRIBUTIONS|{entry.name}"
	existing_name = frappe.db.get_value("Journal Entry", {"custom_malaysia_journal_key": key, "docstatus": ["<", 2]}, "name")
	if existing_name:
		entry.db_set("custom_malaysia_employer_contribution_journal", existing_name, update_modified=False)
		return existing_name
	account_map = employer_contribution_account_map(entry.company)
	totals = {"EPF": Decimal("0"), "SOCSO": Decimal("0"), "EIS": Decimal("0"), "HRD Corp": Decimal("0")}
	slips = frappe.get_all(
		"Salary Slip",
		filters={"payroll_entry": entry.name, "docstatus": 1, "custom_malaysia_statutory_snapshot": ["is", "set"]},
		fields=["name", "custom_malaysia_statutory_snapshot"],
		limit=100000,
	)
	if not slips:
		frappe.throw(_("No submitted Salary Slips with Malaysia statutory snapshots were found."))
	for slip in slips:
		try:
			snapshot = parse_statutory_snapshot(slip.custom_malaysia_statutory_snapshot)
		except ValueError as exc:
			frappe.throw(_("Salary Slip {0} has an invalid statutory snapshot: {1}").format(slip.name, exc))
		for result in snapshot.get("current_results", []):
			if result.get("scheme") in totals:
				totals[result["scheme"]] += Decimal(str(result.get("employer_amount") or 0))
	cost_center = entry.cost_center or frappe.db.get_value("Company", entry.company, "cost_center")
	if not cost_center:
		frappe.throw(_("A Cost Center is required for employer contribution accounting."))
	journal = frappe.new_doc("Journal Entry")
	journal.voucher_type = "Journal Entry"
	journal.company = entry.company
	journal.posting_date = entry.posting_date
	journal.user_remark = f"Malaysia employer statutory contributions for Payroll Entry {entry.name}"
	journal.custom_malaysia_payroll_entry = entry.name
	journal.custom_malaysia_journal_key = key
	for scheme in ("EPF", "SOCSO", "EIS", "HRD Corp"):
		amount = totals[scheme].quantize(Decimal("0.01"))
		if not amount:
			continue
		expense, payable = account_map[scheme]
		absolute = abs(amount)
		if amount > 0:
			journal.append("accounts", {"account": expense, "debit_in_account_currency": float(absolute), "credit_in_account_currency": 0, "cost_center": cost_center})
			journal.append("accounts", {"account": payable, "debit_in_account_currency": 0, "credit_in_account_currency": float(absolute)})
		else:
			journal.append("accounts", {"account": payable, "debit_in_account_currency": float(absolute), "credit_in_account_currency": 0})
			journal.append("accounts", {"account": expense, "debit_in_account_currency": 0, "credit_in_account_currency": float(absolute), "cost_center": cost_center})
	if not journal.accounts:
		entry.db_set("custom_malaysia_employer_contribution_total", 0, update_modified=True)
		return None
	journal.insert(ignore_permissions=True)
	journal.submit()
	total = sum(totals.values(), Decimal("0"))
	frappe.db.set_value(
		"Payroll Entry",
		entry.name,
		{"custom_malaysia_employer_contribution_journal": journal.name, "custom_malaysia_employer_contribution_total": total},
		update_modified=True,
	)
	return journal.name


def cancel_employer_contribution_journal(*, payroll_entry) -> None:
	entry = frappe.get_doc("Payroll Entry", payroll_entry) if isinstance(payroll_entry, str) else payroll_entry
	name = entry.custom_malaysia_employer_contribution_journal or frappe.db.get_value(
		"Journal Entry", {"custom_malaysia_journal_key": f"EMPLOYER-CONTRIBUTIONS|{entry.name}", "docstatus": ["<", 2]}, "name"
	)
	if name and frappe.db.exists("Journal Entry", name):
		journal = frappe.get_doc("Journal Entry", name)
		if journal.docstatus == 1:
			journal.flags.ignore_permissions = True
			journal.cancel()
		elif journal.docstatus == 0:
			frappe.delete_doc("Journal Entry", journal.name, ignore_permissions=True, force=True)
	frappe.db.set_value(
		"Payroll Entry",
		entry.name,
		{"custom_malaysia_employer_contribution_journal": None, "custom_malaysia_employer_contribution_total": 0},
		update_modified=True,
	)
