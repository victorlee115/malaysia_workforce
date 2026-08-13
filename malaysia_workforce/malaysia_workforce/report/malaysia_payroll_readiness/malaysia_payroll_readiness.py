import frappe
from frappe import _

from malaysia_workforce.payroll.events import employee_readiness
from malaysia_workforce.payroll.validation import hrd_registration_issues


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.company:
		frappe.throw(_("Company is required."))
	frappe.get_doc("Company", filters.company).check_permission("read")
	columns = [
		{"fieldname":"employee","label":_("Employee"),"fieldtype":"Link","options":"Employee","width":140},
		{"fieldname":"employee_name","label":_("Employee Name"),"fieldtype":"Data","width":180},
		{"fieldname":"status","label":_("Status"),"fieldtype":"Data","width":100},
		{"fieldname":"issues","label":_("What needs attention"),"fieldtype":"Data","width":500},
	]
	rows = []
	company_issues = hrd_registration_issues(filters.company, filters.payroll_date)
	if company_issues:
		rows.append({"employee_name": _("Company setup"), "status": "Needs Attention",
			"issues": " ".join(company_issues), "indicator": "red"})
	for employee in frappe.get_list("Employee", filters={"company": filters.company, "status": "Active"}, fields=["name", "employee_name"]):
		issues = employee_readiness(employee.name, filters.company, filters.payroll_date)
		if not issues and not filters.show_ready:
			continue
		rows.append({"employee": employee.name, "employee_name": employee.employee_name,
			"status": "Needs Attention" if issues else "Ready", "issues": " ".join(issues),
			"indicator": "red" if issues else "green"})
	return columns, rows
