from collections import defaultdict
from decimal import Decimal

import frappe
from frappe import _

from malaysia_workforce.payroll.profile import (
	STATUTORY_PROFILE_FIELD,
	is_socso_eis_lindung_profile,
	normalize_statutory_profile,
)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.company:
		frappe.throw(_("Company is required."))
	frappe.get_doc("Company", filters.company).check_permission("read")
	columns = [
		{"fieldname":"employee","label":_("Employee"),"fieldtype":"Link","options":"Employee","width":130},
		{"fieldname":"employee_name","label":_("Employee Name"),"fieldtype":"Data","width":180},
		{"fieldname":"profile","label":_("Statutory Profile"),"fieldtype":"Data","width":220},
		*[{"fieldname": key, "label": label, "fieldtype":"Currency", "width":120} for key, label in (
			("gross_pay", _("Gross Pay")), ("epf_employee", _("EPF Employee")), ("epf_employer", _("EPF Employer")),
			("socso_employee", _("SOCSO Employee")), ("socso_employer", _("SOCSO Employer")),
			("eis_employee", _("EIS Employee")), ("eis_employer", _("EIS Employer")),
			("pcb", _("PCB")), ("cp38", _("CP38")), ("zakat", _("Zakat")), ("net_pay", _("Net Pay")))]
	]
	names = frappe.get_list(
		"Salary Slip",
		filters={"company": filters.company, "docstatus": 1,
			"end_date": ["between", [f"{int(filters.year)}-01-01", f"{int(filters.year)}-12-31"]]},
		pluck="name",
	)
	if not names:
		return columns, []
	slips = frappe.get_all(
		"Salary Slip",
		filters={"name": ["in", names]},
		fields=["name", "employee", "employee_name", "gross_pay", "net_pay", "end_date", STATUTORY_PROFILE_FIELD],
		order_by="end_date, name",
	)
	if not filters.show_all_profiles:
		slips = [slip for slip in slips if not is_socso_eis_lindung_profile(slip.get(STATUTORY_PROFILE_FIELD))]
	if not slips:
		return columns, []
	data = defaultdict(lambda: defaultdict(lambda: Decimal("0")))
	latest = {}
	employee_by_slip = {row.name: row.employee for row in slips}
	for slip in slips:
		data[slip.employee]["employee_name"] = slip.employee_name
		data[slip.employee]["gross_pay"] += Decimal(str(slip.gross_pay or 0))
		data[slip.employee]["net_pay"] += Decimal(str(slip.net_pay or 0))
		current = latest.get(slip.employee)
		if current is None or (slip.end_date, slip.name) >= (current.end_date, current.name):
			latest[slip.employee] = slip
	for employee, slip in latest.items():
		data[employee]["profile"] = normalize_statutory_profile(slip.get(STATUTORY_PROFILE_FIELD))
	for row in frappe.get_all(
		"Malaysia Statutory Result",
		filters={"parent": ["in", [s.name for s in slips]], "parenttype": "Salary Slip"},
		fields=["parent", "scheme", "employee_amount", "employer_amount", "extra_employee_amount"],
	):
		employee = employee_by_slip[row.parent]
		key = row.scheme.lower().replace(" corp", "").replace(" ", "_")
		if row.scheme == "EPF":
			data[employee]["epf_employee"] += Decimal(str(row.employee_amount or 0))
			data[employee]["epf_employer"] += Decimal(str(row.employer_amount or 0))
		elif row.scheme == "SOCSO":
			data[employee]["socso_employee"] += Decimal(str(row.employee_amount or 0)) + Decimal(str(row.extra_employee_amount or 0))
			data[employee]["socso_employer"] += Decimal(str(row.employer_amount or 0))
		elif row.scheme == "EIS":
			data[employee]["eis_employee"] += Decimal(str(row.employee_amount or 0))
			data[employee]["eis_employer"] += Decimal(str(row.employer_amount or 0))
		elif row.scheme in {"PCB", "CP38", "Zakat"}:
			data[employee][key] += Decimal(str(row.employee_amount or 0))
	return columns, [{"employee": employee, **values} for employee, values in sorted(data.items())]
