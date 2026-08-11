from __future__ import annotations

import json
from collections import defaultdict
from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import add_days, getdate

from malaysia_workforce.forms.validation import validate_tax_year, validate_tp1_rows, validate_tp3_values
from malaysia_workforce.statutory.snapshot import parse_statutory_snapshot
from malaysia_workforce.utils import ensure_roles, get_current_employee

FORM_PRINT_FORMATS = {
	"Malaysia Tax Declaration TP1": "Malaysia TP1 2026",
	"Malaysia Previous Employment TP3": "Malaysia TP3 2026",
	"Malaysia Employee Notification": "Malaysia Employee Notification",
	"Malaysia Annual Remuneration Statement": "Malaysia EA EC Statement",
}


def generate_document_pdf(doctype: str, name: str) -> bytes:
	if doctype not in FORM_PRINT_FORMATS:
		frappe.throw(_("No Malaysia PDF renderer is registered for {0}.").format(doctype))
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	return frappe.get_print(doctype, name, print_format=FORM_PRINT_FORMATS[doctype], as_pdf=True)


def create_employee_notification(employee: str, form_type: str, trigger_date, **values):
	ensure_roles("Malaysia HR Manager", "HR Manager", "HR User", "System Manager")
	if form_type not in {"CP21", "CP22", "CP22A"}:
		frappe.throw(_("Unsupported employee notification form."))
	company = frappe.db.get_value("Employee", employee, "company")
	if not company:
		frappe.throw(_("Employee {0} does not exist.").format(employee))
	frappe.get_doc("Employee", employee).check_permission("read")
	trigger_date = getdate(trigger_date)
	existing = frappe.db.get_value(
		"Malaysia Employee Notification",
		{
			"employee": employee,
			"company": company,
			"form_type": form_type,
			"trigger_date": trigger_date,
			"status": ["!=", "Cancelled"],
		},
		"name",
	)
	if existing:
		return existing
	doc = frappe.new_doc("Malaysia Employee Notification")
	doc.employee = employee
	doc.company = company
	doc.form_type = form_type
	doc.trigger_date = trigger_date
	event_type = values.get("event_type") or {"CP22": "Commencement", "CP21": "Departure"}.get(
		form_type, "Cessation"
	)
	doc.event_type = event_type
	if form_type == "CP22":
		doc.due_date = add_days(trigger_date, 30)
	elif form_type == "CP22A" and event_type == "Death":
		doc.due_date = add_days(trigger_date, 30)
	else:
		doc.due_date = add_days(trigger_date, -30)
	for key in (
		"cessation_date",
		"departure_date",
		"death_date",
		"last_working_day",
		"reason",
		"amount_withheld",
		"withholding_required",
		"withholding_until",
	):
		if key in values:
			setattr(doc, key, values[key])
	doc.insert()
	return doc.name


def _decimal(value) -> Decimal:
	return Decimal(str(value or 0))


def generate_annual_statements(company: str, tax_year: int) -> list[str]:
	ensure_roles(
		"Statutory Administrator",
		"Malaysia Payroll User",
		"HR Manager",
		"Malaysia HR Manager",
		"System Manager",
	)
	frappe.get_doc("Company", company).check_permission("read")
	from malaysia_workforce.compliance.scope import assert_rule_review_current

	assert_rule_review_current(company, f"{int(tax_year)}-12-31")
	start, end = getdate(f"{tax_year}-01-01"), getdate(f"{tax_year}-12-31")
	slips = frappe.get_all(
		"Salary Slip",
		filters={
			"company": company,
			"docstatus": 1,
			"end_date": ["between", [start, end]],
			"custom_malaysia_statutory_snapshot": ["is", "set"],
		},
		fields=["employee", "custom_malaysia_statutory_snapshot"],
		limit=50000,
	)
	data = defaultdict(lambda: defaultdict(lambda: Decimal("0")))
	for slip in slips:
		try:
			snapshot = parse_statutory_snapshot(slip.custom_malaysia_statutory_snapshot)
		except ValueError as exc:
			frappe.throw(_("A submitted Salary Slip has an invalid Malaysia statutory snapshot: {0}").format(exc))
		bases = snapshot.get("current_wage_bases", {})
		data[slip.employee]["gross"] += _decimal(bases.get("gross"))
		data[slip.employee]["cp38"] += _decimal(snapshot.get("current_cp38"))
		data[slip.employee]["zakat"] += _decimal(snapshot.get("current_zakat"))
		for result in snapshot.get("current_results", []):
			amount = _decimal(result.get("employee_amount")) + _decimal(result.get("extra_employee_amount"))
			scheme = result.get("scheme")
			if scheme == "EPF":
				data[slip.employee]["epf"] += amount
			elif scheme in {"SOCSO", "LINDUNG 24 Jam"}:
				data[slip.employee]["socso"] += amount
			elif scheme == "EIS":
				data[slip.employee]["eis"] += amount
			elif scheme == "PCB":
				data[slip.employee]["pcb"] += amount

	created: list[str] = []
	for employee, totals in data.items():
		existing = frappe.get_all(
			"Malaysia Annual Remuneration Statement",
			filters={"employee": employee, "company": company, "tax_year": tax_year, "form_type": "EA"},
			fields=["name", "revision", "status"],
			order_by="revision desc, creation desc",
			limit=1,
		)
		latest = existing[0] if existing else None
		name = latest.name if latest and latest.status not in {"Issued", "Corrected"} else None
		doc = (
			frappe.get_doc("Malaysia Annual Remuneration Statement", name)
			if name
			else frappe.new_doc("Malaysia Annual Remuneration Statement")
		)
		if not name:
			doc.employee = employee
			doc.company = company
			doc.tax_year = tax_year
			doc.form_type = "EA"
			doc.revision = int(latest.revision or 0) + 1 if latest else 0
		doc.gross_remuneration = totals["gross"]
		doc.epf_employee = totals["epf"]
		doc.socso_employee = totals["socso"]
		doc.eis_employee = totals["eis"]
		doc.pcb = totals["pcb"]
		doc.cp38 = totals["cp38"]
		doc.zakat = totals["zakat"]
		doc.generated_from_snapshot = json.dumps(
			{key: str(value) for key, value in totals.items()}, sort_keys=True
		)
		doc.status = "Generated"
		doc.save(ignore_permissions=True)
		created.append(doc.name)
	return created


def _parse_rows(value, tax_year: int) -> list[dict]:
	rows = frappe.parse_json(value) if isinstance(value, str) else value
	try:
		return validate_tp1_rows(rows, tax_year=tax_year)
	except ValueError as exc:
		frappe.throw(_(str(exc)))


@frappe.whitelist(methods=["POST"])
def employee_submit_tp1(tax_year: int, relief_claims: str | list[dict], declaration: int = 0):
	employee = get_current_employee()
	company = frappe.db.get_value("Employee", employee, "company")
	if not company:
		frappe.throw(_("No Company is linked to your Employee record."), frappe.PermissionError)
	try:
		year = validate_tax_year(tax_year, getdate().year)
	except ValueError as exc:
		frappe.throw(_(str(exc)))
	if int(declaration or 0) != 1:
		frappe.throw(_("The employee declaration must be accepted before submission."))
	doc = frappe.new_doc("Malaysia Tax Declaration TP1")
	doc.employee = employee
	doc.company = company
	doc.tax_year = year
	doc.status = "Submitted by Employee"
	doc.employee_declaration = 1
	for row in _parse_rows(relief_claims, year):
		doc.append("relief_claims", row)
	doc.insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist(methods=["POST"])
def employee_submit_tp3(
	tax_year: int,
	previous_employer_name: str,
	previous_employer_number: str | None = None,
	employment_start: str | None = None,
	employment_end: str | None = None,
	gross_normal_remuneration: float = 0,
	gross_additional_remuneration: float = 0,
	epf_contribution: float = 0,
	mtd_paid: float = 0,
	zakat_paid: float = 0,
	optional_reliefs: float = 0,
	employee_declaration: int = 0,
):
	employee = get_current_employee()
	company = frappe.db.get_value("Employee", employee, "company")
	if not company:
		frappe.throw(_("No Company is linked to your Employee record."), frappe.PermissionError)
	try:
		values = validate_tp3_values(
			{
				"tax_year": tax_year,
				"previous_employer_name": previous_employer_name,
				"previous_employer_number": previous_employer_number,
				"employment_start": employment_start,
				"employment_end": employment_end,
				"gross_normal_remuneration": gross_normal_remuneration,
				"gross_additional_remuneration": gross_additional_remuneration,
				"epf_contribution": epf_contribution,
				"mtd_paid": mtd_paid,
				"zakat_paid": zakat_paid,
				"optional_reliefs": optional_reliefs,
				"employee_declaration": employee_declaration,
			},
			getdate().year,
		)
	except ValueError as exc:
		frappe.throw(_(str(exc)))
	doc = frappe.new_doc("Malaysia Previous Employment TP3")
	doc.employee = employee
	doc.company = company
	for key, value in values.items():
		setattr(doc, key, value)
	doc.status = "Submitted by Employee"
	doc.insert(ignore_permissions=True)
	return doc.name
