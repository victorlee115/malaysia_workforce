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
from malaysia_workforce.utils import ensure_roles, validate_date_range


PAY_ENGINE_VERSION = "MW-PAY-2026.2"


def _ensure_permission():
	ensure_roles("Malaysia Payroll User", "HR Manager", "Malaysia HR Manager", "System Manager")


def _employee_scope(run) -> set[str] | None:
	filters = {"company": run.company, "status": "Active"}
	if run.branch:
		filters["branch"] = run.branch
	if run.department:
		filters["department"] = run.department
	if not run.branch and not run.department:
		return None
	return set(frappe.get_all("Employee", filters=filters, pluck="name", limit_page_length=100000))


def _work_records(run, *, include_other_runs: bool = False):
	rows = frappe.get_all(
		"Shift Work Record",
		filters={
			"company": run.company,
			"work_date": ["between", [run.start_date, run.end_date]],
			"docstatus": 1,
			"status": ["in", ["Approved", "Automatically Verified", "Payroll Generated"]],
		},
		fields=[
			"name",
			"employee",
			"gross_pay",
			"status",
			"additional_salary_references",
			"work_date",
			"payroll_run",
		],
		order_by="employee, work_date, name",
		limit_page_length=100000,
	)
	scope = _employee_scope(run)
	return [
		row
		for row in rows
		if (scope is None or row.employee in scope)
		and (include_other_runs or not row.payroll_run or row.payroll_run == run.name)
	]


def _conflicting_work_records(run) -> list:
	return [
		row
		for row in _work_records(run, include_other_runs=True)
		if row.payroll_run and row.payroll_run != run.name
	]


def _lock_and_reserve_work_records(run) -> list:
	"""Lock and reserve the exact payable records in the current database transaction."""
	conditions = [
		"company=%s",
		"work_date BETWEEN %s AND %s",
		"docstatus=1",
		"status IN ('Approved','Automatically Verified','Payroll Generated')",
	]
	values: list = [run.company, run.start_date, run.end_date]
	scope = _employee_scope(run)
	if scope is not None:
		if not scope:
			return []
		placeholders = ", ".join(["%s"] * len(scope))
		conditions.append(f"employee IN ({placeholders})")
		values.extend(sorted(scope))
	rows = frappe.db.sql(
		f"""
		SELECT name, employee, gross_pay, status, additional_salary_references,
			work_date, payroll_run, pre_payroll_status
		FROM `tabShift Work Record`
		WHERE {' AND '.join(conditions)}
		ORDER BY employee, work_date, name
		FOR UPDATE
		""",
		values,
		as_dict=True,
	)
	conflicts = [row for row in rows if row.payroll_run and row.payroll_run != run.name]
	if conflicts:
		frappe.throw(
			_("Work records are already reserved by another payroll run: {0}").format(
				", ".join(f"{row.name} ({row.payroll_run})" for row in conflicts[:20])
			)
		)
	if not rows:
		return []
	names = sorted(row.name for row in rows)
	current_hash = _source_hash(names)
	if run.source_work_record_hash and run.source_work_record_hash != current_hash:
		frappe.throw(_("The work-record set has changed. Create an adjustment payroll run."))
	for row in rows:
		if not row.payroll_run:
			frappe.db.set_value(
				"Shift Work Record",
				row.name,
				{
					"payroll_run": run.name,
					"pre_payroll_status": row.pre_payroll_status or row.status,
				},
				update_modified=False,
			)
			row.payroll_run = run.name
			row.pre_payroll_status = row.pre_payroll_status or row.status
	return rows


def _unresolved_records(run):
	rows = frappe.get_all(
		"Shift Work Record",
		filters={
			"company": run.company,
			"work_date": ["between", [run.start_date, run.end_date]],
			"docstatus": 0,
			"status": ["not in", ["Cancelled"]],
		},
		fields=["name", "employee", "status", "payroll_run"],
		limit_page_length=100000,
	)
	scope = _employee_scope(run)
	return [row for row in rows if (scope is None or row.employee in scope) and (not row.payroll_run or row.payroll_run == run.name)]


def _current_assignment(employee: str, company: str, on_date):
	rows = frappe.get_all(
		"Salary Structure Assignment",
		filters={"employee": employee, "company": company, "docstatus": 1, "from_date": ["<=", on_date]},
		fields=["name", "salary_structure", "from_date", "payroll_payable_account"],
		order_by="from_date desc, creation desc",
		limit_page_length=20,
	)
	return rows[0] if rows else None


def _assignment_effective_date(employee: str, run):
	joining_date = frappe.db.get_value("Employee", employee, "date_of_joining")
	if joining_date and getdate(joining_date) > getdate(run.start_date):
		return getdate(joining_date)
	return getdate(run.start_date)


def _validate_assignment(employee: str, run) -> str | None:
	effective_date = _assignment_effective_date(employee, run)
	assignment = _current_assignment(employee, run.company, effective_date)
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
	if structure.company != run.company:
		return f"Salary Structure {assignment.salary_structure} belongs to another company"
	if structure.payroll_frequency and structure.payroll_frequency != run.payroll_frequency:
		return (
			f"Salary Structure {assignment.salary_structure} uses {structure.payroll_frequency}, "
			f"not {run.payroll_frequency}"
		)
	return None


def _source_hash(names: list[str]) -> str:
	return hashlib.sha256("\n".join(sorted(names)).encode("utf-8")).hexdigest()


def collect_and_validate_run(run):
	_ensure_permission()
	validate_date_range(run.start_date, run.end_date, "payroll run")
	run.status = "Collecting"
	run.save()
	errors: list[str] = []
	warnings: list[str] = []
	company = frappe.get_cached_doc("Company", run.company)
	if not company.custom_enable_malaysia_payroll:
		errors.append("Malaysia payroll is not enabled on the Company record.")
	if not (run.payroll_payable_account or company.default_payroll_payable_account):
		errors.append("No Payroll Payable Account is configured.")
	if not (run.cost_center or company.cost_center):
		errors.append("No Cost Center is configured.")
	settings = frappe.get_cached_doc("Malaysia Workforce Settings")
	if settings.auto_create_employer_contribution_journal:
		try:
			employer_contribution_account_map(run.company)
		except (frappe.ValidationError, frappe.PermissionError) as exc:
			errors.append(str(exc))
	if settings.strict_rule_review and settings.rules_reviewed_through and getdate(run.end_date) > getdate(settings.rules_reviewed_through):
		errors.append(f"Statutory rules were only reviewed through {settings.rules_reviewed_through}.")

	for row in _unresolved_records(run):
		errors.append(f"{row.name}: employee {row.employee} is still {row.status}.")

	for row in _conflicting_work_records(run):
		errors.append(f"{row.name}: already reserved by payroll run {row.payroll_run}.")

	records = _work_records(run)
	if not records:
		errors.append("No submitted, approved Shift Work Records were found for this run.")
	employees = sorted({row.employee for row in records})
	for employee in employees:
		agreement = get_work_agreement(employee, run.end_date)
		if not agreement:
			errors.append(f"{employee}: no active Employee Work Agreement.")
		profile = get_malaysia_profile(employee)
		if not profile:
			errors.append(f"{employee}: no Malaysia Employee Profile.")
			continue
		assignment_error = _validate_assignment(employee, run)
		if assignment_error:
			errors.append(f"{employee}: {assignment_error}. Use 'Create missing casual assignments' only when appropriate.")
		for scheme, registration_field in (("EPF", "epf_number"), ("SOCSO", "socso_number"), ("EIS", "eis_number")):
			treatment, _, _ = get_scheme_treatment(employee, scheme, run.end_date)
			if treatment == "Pending Review":
				errors.append(f"{employee}: {scheme} treatment is Pending Review.")
			elif treatment != "Not Applicable" and not profile.get(registration_field):
				errors.append(f"{employee}: {scheme} registration number is missing.")
		pcb_treatment, _, _ = get_scheme_treatment(employee, "PCB", run.end_date)
		if pcb_treatment == "Pending Review":
			errors.append(f"{employee}: PCB treatment is Pending Review.")
		elif pcb_treatment != "Not Applicable" and not profile.income_tax_number:
			warnings.append(f"{employee}: income tax number is missing; LHDN output validation may fail.")

	for row in records:
		if Decimal(str(row.gross_pay or 0)) < Decimal("0"):
			errors.append(f"{row.name}: gross pay cannot be negative.")

	current_names = sorted(row.name for row in records)
	current_hash = _source_hash(current_names)
	if run.source_work_record_hash and run.source_work_record_hash != current_hash:
		errors.append(
			"The approved work-record set changed after this payroll run was frozen. Create an adjustment payroll run instead."
		)

	run.approved_work_records = len(records)
	run.work_records_total = sum((Decimal(str(row.gross_pay or 0)) for row in records), Decimal("0"))
	run.validation_errors = json.dumps({"errors": errors, "warnings": warnings}, indent=2)
	run.status = "Validation Failed" if errors else "Ready"
	run.last_processed_on = now_datetime()
	run.save()
	return {
		"status": run.status,
		"errors": errors,
		"warnings": warnings,
		"record_count": len(records),
		"gross": run.work_records_total,
	}


def _batch_key(run_name: str, employee: str, component: str) -> str:
	return hashlib.sha256(f"{run_name}|{employee}|{component}".encode()).hexdigest()


def generate_additional_salaries(run):
	_ensure_permission()
	validation = collect_and_validate_run(run)
	if validation["errors"]:
		frappe.throw(_("Resolve payroll readiness errors before generating Additional Salary records."))

	records = _lock_and_reserve_work_records(run)
	if not records:
		frappe.throw(_("No payable Shift Work Records are available for reservation."))
	record_names = sorted(row.name for row in records)
	current_hash = _source_hash(record_names)
	if not run.source_work_record_hash:
		run.source_work_record_hash = current_hash
		run.source_work_record_names = json.dumps(record_names, indent=2)
		run.save()

	settings = frappe.get_cached_doc("Malaysia Workforce Settings")
	component_map = {
		"Casual Ordinary Pay": settings.casual_ordinary_component,
		"Part-Time Additional Hours": settings.casual_additional_component,
		"Casual Overtime Pay": settings.casual_overtime_component,
		"Rest Day Pay": settings.rest_day_component,
		"Public Holiday Pay": settings.public_holiday_component,
	}
	aggregates = defaultdict(lambda: {"amount": Decimal("0"), "records": []})
	for row in records:
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
	if not aggregates:
		frappe.throw(_("No payable pay-breakdown lines were found."))

	created: list[str] = []
	by_employee: dict[str, list[str]] = defaultdict(list)
	for (employee, component), data in sorted(aggregates.items()):
		key = _batch_key(run.name, employee, component)
		existing = frappe.db.get_value(
			"Additional Salary",
			{"custom_source_batch_key": key, "docstatus": ["<", 2]},
			[
				"name",
				"amount",
				"employee",
				"company",
				"salary_component",
				"payroll_date",
				"overwrite_salary_structure_amount",
				"ref_doctype",
				"ref_docname",
				"custom_generated_by_malaysia_workforce",
			],
			as_dict=True,
		)
		expected_amount = float(data["amount"])
		if existing:
			if (
				existing.employee != employee
				or existing.company != run.company
				or existing.salary_component != component
				or getdate(existing.payroll_date) != getdate(run.payroll_date)
				or int(existing.overwrite_salary_structure_amount or 0) != 0
				or existing.ref_doctype != "Malaysia Payroll Run"
				or existing.ref_docname != run.name
				or not int(existing.custom_generated_by_malaysia_workforce or 0)
				or abs(float(existing.amount or 0) - expected_amount) > 0.001
			):
				frappe.throw(_("Existing Additional Salary {0} does not match the frozen payroll batch.").format(existing.name))
			name = existing.name
		else:
			doc = frappe.new_doc("Additional Salary")
			doc.employee = employee
			doc.company = run.company
			doc.salary_component = component
			doc.amount = expected_amount
			doc.payroll_date = run.payroll_date
			doc.overwrite_salary_structure_amount = 0
			doc.ref_doctype = "Malaysia Payroll Run"
			doc.ref_docname = run.name
			doc.custom_generated_by_malaysia_workforce = 1
			doc.custom_source_batch_key = key
			doc.custom_pay_calculation_version = PAY_ENGINE_VERSION
			doc.insert(ignore_permissions=True)
			doc.submit()
			name = doc.name
		created.append(name)
		by_employee[employee].append(name)

	for row in records:
		frappe.db.set_value(
			"Shift Work Record",
			row.name,
			{
				"status": "Payroll Generated",
				"pre_payroll_status": row.pre_payroll_status or row.status,
				"payroll_run": run.name,
				"payroll_date": run.payroll_date,
				"additional_salary_references": "\n".join(sorted(by_employee[row.employee])),
			},
			update_modified=True,
		)
	run.additional_salary_count = len(created)
	run.status = "Payroll Generated"
	run.last_processed_on = now_datetime()
	run.save()
	return created


def release_work_record_reservations(run, *, reset_run: bool = True) -> int:
	"""Release a draft run after all generated payroll documents have been cancelled."""
	_ensure_permission()
	if isinstance(run, str):
		run = frappe.get_doc("Malaysia Payroll Run", run)
	if run.payroll_entry and frappe.db.exists("Payroll Entry", run.payroll_entry):
		frappe.throw(_("Cancel and delete the linked Payroll Entry before resetting this run."))
	if frappe.db.exists(
		"Additional Salary",
		{"ref_doctype": "Malaysia Payroll Run", "ref_docname": run.name, "docstatus": ["<", 2]},
	):
		frappe.throw(_("Cancel all generated Additional Salary records before resetting this run."))
	rows = frappe.get_all(
		"Shift Work Record",
		filters={"payroll_run": run.name},
		fields=["name", "status", "pre_payroll_status", "additional_salary_references"],
		limit_page_length=100000,
	)
	for row in rows:
		if row.additional_salary_references:
			frappe.throw(_("Shift Work Record {0} still contains payroll references.").format(row.name))
		frappe.db.set_value(
			"Shift Work Record",
			row.name,
			{
				"status": row.pre_payroll_status or "Approved",
				"pre_payroll_status": "",
				"payroll_run": "",
				"payroll_date": None,
			},
			update_modified=True,
		)
	if reset_run:
		run.source_work_record_hash = ""
		run.source_work_record_names = ""
		run.additional_salary_count = 0
		run.status = "Draft"
		run.last_processed_on = now_datetime()
		run.save()
	return len(rows)


def ensure_casual_salary_structure(company: str, payroll_frequency: str) -> str:
	name = f"Malaysia Casual - {company} - {payroll_frequency}"
	company_doc = frappe.get_cached_doc("Company", company)
	settings = frappe.get_cached_doc("Malaysia Workforce Settings")
	component = settings.casual_ordinary_component
	if not component or not frappe.db.exists("Salary Component", component):
		frappe.throw(_("Configure a valid Casual Ordinary Salary Component before creating assignments."))

	if frappe.db.exists("Salary Structure", name):
		structure = frappe.get_doc("Salary Structure", name)
		problems = []
		if structure.company != company:
			problems.append(_("company is {0}").format(structure.company))
		if structure.currency != company_doc.default_currency:
			problems.append(_("currency is {0}").format(structure.currency))
		if structure.payroll_frequency != payroll_frequency:
			problems.append(_("frequency is {0}").format(structure.payroll_frequency))
		if structure.is_active != "Yes" or int(structure.docstatus or 0) != 1:
			problems.append(_("structure is not submitted and active"))
		if component not in {row.salary_component for row in structure.earnings}:
			problems.append(_("ordinary component {0} is missing").format(component))
		if problems:
			frappe.throw(
				_("Reserved Salary Structure {0} is incompatible: {1}. Resolve it manually.").format(
					frappe.bold(name), "; ".join(problems)
				),
				title=_("Casual Salary Structure Conflict"),
			)
		return name

	structure = frappe.new_doc("Salary Structure")
	structure.name = name
	structure.company = company
	structure.currency = company_doc.default_currency
	structure.payroll_frequency = payroll_frequency
	structure.is_active = "Yes"
	structure.append("earnings", {"salary_component": component, "amount": 0})
	structure.insert(ignore_permissions=True)
	structure.submit()
	return name


def create_missing_casual_assignments(run):
	_ensure_permission()
	structure = ensure_casual_salary_structure(run.company, run.payroll_frequency)
	employees = sorted({row.employee for row in _work_records(run)})
	created = []
	company = frappe.get_cached_doc("Company", run.company)
	payable = run.payroll_payable_account or company.default_payroll_payable_account
	if not payable:
		frappe.throw(_("Set a Default Payroll Payable Account before creating assignments."))
	for employee in employees:
		effective_date = _assignment_effective_date(employee, run)
		current = _current_assignment(employee, run.company, effective_date)
		if current:
			if _validate_assignment(employee, run):
				frappe.throw(
					_("Employee {0} already has an incompatible salary assignment. Review it manually.").format(employee)
				)
			continue
		work_arrangement, roster_enabled = frappe.db.get_value(
			"Employee", employee, ["custom_work_arrangement", "custom_roster_enabled"]
		) or (None, None)
		if work_arrangement not in {"Casual", "Part Time", "Temporary", "Seasonal"} or not roster_enabled:
			frappe.throw(
				_("Employee {0} is not configured as a roster-enabled flexible worker; create the assignment manually.").format(employee)
			)
		assignment = frappe.new_doc("Salary Structure Assignment")
		assignment.employee = employee
		assignment.salary_structure = structure
		assignment.from_date = effective_date
		assignment.company = run.company
		assignment.base = 0
		assignment.payroll_payable_account = payable
		assignment.insert(ignore_permissions=True)
		assignment.submit()
		created.append(assignment.name)
	return created


def create_payroll_entry(run):
	_ensure_permission()
	if not run.source_work_record_hash:
		generate_additional_salaries(run)
	if run.payroll_entry and frappe.db.exists("Payroll Entry", run.payroll_entry):
		return run.payroll_entry
	company = frappe.get_cached_doc("Company", run.company)
	payable = run.payroll_payable_account or company.default_payroll_payable_account
	if not payable:
		frappe.throw(_("Set a Default Payroll Payable Account on the Company or this payroll run."))
	cost_center = run.cost_center or company.cost_center
	if not cost_center:
		frappe.throw(_("Set a Cost Center on the Company or this payroll run."))
	expected_employees = sorted({row.employee for row in _work_records(run) if row.payroll_run == run.name})
	if not expected_employees:
		frappe.throw(_("This payroll run has no frozen work records."))

	entry = frappe.new_doc("Payroll Entry")
	entry.flags.ignore_permissions = True
	entry.company = run.company
	entry.posting_date = run.payroll_date
	entry.start_date = run.start_date
	entry.end_date = run.end_date
	entry.payroll_frequency = run.payroll_frequency
	entry.currency = company.default_currency
	entry.exchange_rate = 1
	entry.payroll_payable_account = payable
	entry.cost_center = cost_center
	entry.branch = run.branch
	entry.department = run.department
	entry.salary_slip_based_on_timesheet = 0
	entry.custom_malaysia_payroll_run = run.name
	entry.insert(ignore_permissions=True)
	entry.fill_employee_details()
	entry.set("employees", [row for row in entry.employees if row.employee in expected_employees])
	if sorted(row.employee for row in entry.employees) != expected_employees:
		missing = sorted(set(expected_employees) - {row.employee for row in entry.employees})
		frappe.delete_doc("Payroll Entry", entry.name, ignore_permissions=True, force=True)
		frappe.throw(
			_("Payroll Entry could not include these employees: {0}. Check salary assignments.").format(", ".join(missing))
		)
	entry.number_of_employees = len(entry.employees)
	entry.save(ignore_permissions=True)
	run.payroll_entry = entry.name
	run.status = "Payroll Generated"
	run.save()
	return entry.name


def _validated_company_account(account: str | None, company: str, label: str) -> str:
	if not account:
		frappe.throw(_("Configure {0} in Malaysia Workforce Settings.").format(label))
	row = frappe.db.get_value(
		"Account", account, ["company", "is_group", "account_currency"], as_dict=True
	)
	if not row or row.company != company or row.is_group:
		frappe.throw(_("{0} must be a non-group Account belonging to {1}.").format(label, company))
	company_currency = frappe.db.get_value("Company", company, "default_currency")
	if row.account_currency and row.account_currency != company_currency:
		frappe.throw(_("{0} must use the Company's default currency.").format(label))
	return account


def employer_contribution_account_map(company: str) -> dict[str, tuple[str, str]]:
	settings = frappe.get_cached_doc("Malaysia Workforce Settings")
	return {
		"EPF": (
			_validated_company_account(settings.employer_epf_expense_account, company, "Employer EPF Expense Account"),
			_validated_company_account(settings.epf_payable_account, company, "EPF Payable Account"),
		),
		"SOCSO": (
			_validated_company_account(settings.employer_socso_expense_account, company, "Employer SOCSO Expense Account"),
			_validated_company_account(settings.socso_payable_account, company, "SOCSO Payable Account"),
		),
		"EIS": (
			_validated_company_account(settings.employer_eis_expense_account, company, "Employer EIS Expense Account"),
			_validated_company_account(settings.eis_payable_account, company, "EIS Payable Account"),
		),
	}


def create_employer_contribution_journal(run):
	"""Create one idempotent Journal Entry for employer EPF, SOCSO and EIS costs.

	Employee deductions remain in the standard Payroll Entry through the configured
	Salary Component accounts. This journal records only employer-side costs.
	"""
	_ensure_permission()
	if isinstance(run, str):
		run = frappe.get_doc("Malaysia Payroll Run", run)
	if not run.payroll_entry:
		frappe.throw(_("Create and submit the linked Payroll Entry first."))
	payroll_entry = frappe.get_doc("Payroll Entry", run.payroll_entry)
	if payroll_entry.docstatus != 1:
		frappe.throw(_("Payroll Entry must be submitted before employer contributions are accrued."))
	if run.employer_contribution_journal:
		existing = frappe.get_doc("Journal Entry", run.employer_contribution_journal)
		if existing.docstatus < 2:
			return existing.name
	existing_name = frappe.db.get_value(
		"Journal Entry",
		{"custom_malaysia_payroll_run": run.name, "docstatus": ["<", 2]},
		"name",
	)
	if existing_name:
		run.db_set("employer_contribution_journal", existing_name, update_modified=False)
		return existing_name

	account_map = employer_contribution_account_map(run.company)
	totals = {"EPF": Decimal("0"), "SOCSO": Decimal("0"), "EIS": Decimal("0")}
	slips = frappe.get_all(
		"Salary Slip",
		filters={
			"payroll_entry": payroll_entry.name,
			"docstatus": 1,
			"custom_malaysia_payroll_run": run.name,
			"custom_malaysia_statutory_snapshot": ["is", "set"],
		},
		fields=["name", "custom_malaysia_statutory_snapshot"],
		limit_page_length=100000,
	)
	if not slips:
		frappe.throw(_("No submitted Salary Slips with Malaysia statutory snapshots were found."))
	for slip in slips:
		try:
			snapshot = parse_statutory_snapshot(slip.custom_malaysia_statutory_snapshot)
		except ValueError as exc:
			frappe.throw(_("Salary Slip {0} has an invalid statutory snapshot: {1}").format(slip.name, exc))
		for result in snapshot.get("current_results", []):
			scheme = result.get("scheme")
			if scheme in totals:
				totals[scheme] += Decimal(str(result.get("employer_amount") or 0))

	cost_center = run.cost_center or frappe.db.get_value("Company", run.company, "cost_center")
	if not cost_center:
		frappe.throw(_("A Cost Center is required for employer contribution accounting."))
	journal = frappe.new_doc("Journal Entry")
	journal.voucher_type = "Journal Entry"
	journal.company = run.company
	journal.posting_date = payroll_entry.posting_date
	journal.user_remark = f"Malaysia employer statutory contributions for payroll run {run.name}"
	journal.custom_malaysia_payroll_run = run.name
	for scheme in ("EPF", "SOCSO", "EIS"):
		amount = totals[scheme].quantize(Decimal("0.01"))
		if amount == 0:
			continue
		expense_account, payable_account = account_map[scheme]
		if amount > 0:
			journal.append(
				"accounts",
				{
					"account": expense_account,
					"debit_in_account_currency": float(amount),
					"credit_in_account_currency": 0,
					"cost_center": cost_center,
				},
			)
			journal.append(
				"accounts",
				{
					"account": payable_account,
					"debit_in_account_currency": 0,
					"credit_in_account_currency": float(amount),
				},
			)
		else:
			refund = abs(amount)
			journal.append(
				"accounts",
				{
					"account": payable_account,
					"debit_in_account_currency": float(refund),
					"credit_in_account_currency": 0,
				},
			)
			journal.append(
				"accounts",
				{
					"account": expense_account,
					"debit_in_account_currency": 0,
					"credit_in_account_currency": float(refund),
					"cost_center": cost_center,
				},
			)
	if not journal.accounts:
		run.db_set("employer_contribution_total", 0, update_modified=True)
		return None
	journal.insert(ignore_permissions=True)
	journal.submit()
	total = sum((abs(value) for value in totals.values()), Decimal("0"))
	frappe.db.set_value(
		"Malaysia Payroll Run",
		run.name,
		{
			"employer_contribution_journal": journal.name,
			"employer_contribution_total": total,
		},
		update_modified=True,
	)
	return journal.name


def cancel_employer_contribution_journal(run_name: str) -> None:
	name = frappe.db.get_value("Malaysia Payroll Run", run_name, "employer_contribution_journal")
	if not name or not frappe.db.exists("Journal Entry", name):
		return
	journal = frappe.get_doc("Journal Entry", name)
	if journal.docstatus == 1:
		journal.flags.ignore_permissions = True
		journal.cancel()
	elif journal.docstatus == 0:
		frappe.delete_doc("Journal Entry", journal.name, ignore_permissions=True, force=True)
	frappe.db.set_value(
		"Malaysia Payroll Run",
		run_name,
		{"employer_contribution_journal": None, "employer_contribution_total": 0},
		update_modified=True,
	)
