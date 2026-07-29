from __future__ import annotations

import frappe
from frappe import _

ROLES = (
	"Casual Employee",
	"Roster Manager",
	"Malaysia Payroll User",
	"Malaysia HR Manager",
	"Statutory Administrator",
)

EMPLOYMENT_TYPES = ("Part Time", "Casual", "Temporary", "Seasonal")

COMPONENTS = {
	"Casual Ordinary Pay": {"abbr": "COP", "type": "Earning", "epf": 1, "socso": 1, "eis": 1, "pcb": 1, "pcb_type": "Regular Remuneration"},
	"Part-Time Additional Hours": {"abbr": "PTAH", "type": "Earning", "epf": 1, "socso": 1, "eis": 1, "pcb": 1, "pcb_type": "Regular Remuneration"},
	"Casual Overtime Pay": {"abbr": "COT", "type": "Earning", "epf": 0, "socso": 1, "eis": 1, "pcb": 1, "pcb_type": "Additional Remuneration"},
	"Rest Day Pay": {"abbr": "RDP", "type": "Earning", "epf": 0, "socso": 1, "eis": 1, "pcb": 1, "pcb_type": "Additional Remuneration"},
	"Public Holiday Pay": {"abbr": "PHP", "type": "Earning", "epf": 1, "socso": 1, "eis": 1, "pcb": 1, "pcb_type": "Additional Remuneration"},
	"Shift Allowance": {"abbr": "SHA", "type": "Earning", "epf": 1, "socso": 1, "eis": 1, "pcb": 1, "pcb_type": "Regular Remuneration"},
	"Meal Allowance": {"abbr": "MEA", "type": "Earning", "epf": 1, "socso": 1, "eis": 1, "pcb": 1, "pcb_type": "Regular Remuneration"},
	"Travel Allowance": {"abbr": "TRA", "type": "Earning", "epf": 1, "socso": 1, "eis": 1, "pcb": 1, "pcb_type": "Regular Remuneration"},
	"EPF Employee": {"abbr": "EPFE", "type": "Deduction"},
	"SOCSO Employee": {"abbr": "SOC", "type": "Deduction"},
	"SKBBK Employee": {"abbr": "SKB", "type": "Deduction"},
	"EIS Employee": {"abbr": "EIS", "type": "Deduction"},
	"PCB": {"abbr": "PCB", "type": "Deduction"},
	"CP38": {"abbr": "CP38", "type": "Deduction"},
	"Zakat": {"abbr": "ZAK", "type": "Deduction"},
	"Employer EPF": {"abbr": "EEPF", "type": "Employer Contribution"},
	"Employer SOCSO": {"abbr": "ESOC", "type": "Employer Contribution"},
	"Employer EIS": {"abbr": "EEIS", "type": "Employer Contribution"},
}


def create_master_data():
	for role in ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc(
				{
					"doctype": "Role",
					"role_name": role,
					"desk_access": 0 if role == "Casual Employee" else 1,
				}
			).insert(ignore_permissions=True)
	for employment_type in EMPLOYMENT_TYPES:
		if not frappe.db.exists("Employment Type", employment_type):
			frappe.get_doc(
				{"doctype": "Employment Type", "employee_type_name": employment_type}
			).insert(ignore_permissions=True)
	for name, values in COMPONENTS.items():
		_create_or_update_component(name, values)
	_create_print_formats()


def _create_or_update_component(name: str, values: dict):
	expected_type = values["type"]
	exists = bool(frappe.db.exists("Salary Component", name))
	doc = frappe.get_doc("Salary Component", name) if exists else frappe.new_doc("Salary Component")

	if exists and doc.type != expected_type:
		frappe.throw(
			_(
				"Salary Component {0} already exists with type {1}; Malaysia Workforce requires type {2}. "
				"Rename the existing component or resolve the conflict before installing."
			).format(frappe.bold(name), frappe.bold(doc.type), frappe.bold(expected_type)),
			title=_("Reserved Salary Component Conflict"),
		)

	if exists and not int(doc.get("custom_malaysia_component") or 0):
		frappe.throw(
			_(
				"Salary Component {0} already exists but is not managed by Malaysia Workforce. "
				"Rename it or explicitly migrate it after reviewing its formulas, accounts and statutory classification."
			).format(frappe.bold(name)),
			title=_("Reserved Salary Component Conflict"),
		)

	if exists:
		# Never overwrite payroll formulas, account mappings, abbreviations or statutory
		# wage classifications during migrate. Administrators may intentionally tune
		# these effective settings for their own remuneration policies.
		return

	doc.salary_component = name
	doc.type = expected_type
	doc.salary_component_abbr = values["abbr"]
	doc.depends_on_payment_days = 0
	doc.remove_if_zero_valued = 1
	doc.custom_malaysia_component = 1
	doc.custom_include_in_epf_wages = int(values.get("epf", 0)) if expected_type == "Earning" else 0
	doc.custom_include_in_socso_wages = int(values.get("socso", 0)) if expected_type == "Earning" else 0
	doc.custom_include_in_eis_wages = int(values.get("eis", 0)) if expected_type == "Earning" else 0
	doc.custom_include_in_pcb_remuneration = int(values.get("pcb", 0)) if expected_type == "Earning" else 0
	doc.custom_pcb_remuneration_type = values.get("pcb_type", "") if expected_type == "Earning" else ""
	doc.custom_include_in_lindung_wages = 0
	doc.custom_include_in_hrd_levy_wages = 0
	doc.variable_based_on_taxable_salary = 0
	doc.statistical_component = 0
	doc.do_not_include_in_total = 0
	doc.do_not_include_in_accounts = 0
	doc.accrual_component = 0
	doc.is_flexible_benefit = 0
	doc.deduct_full_tax_on_selected_payroll_date = 0
	doc.is_tax_applicable = int(values.get("pcb", 0)) if expected_type == "Earning" else 0
	doc.insert(ignore_permissions=True)


def _create_print_formats():
	from malaysia_workforce.setup.print_formats import PRINT_FORMATS

	for name, definition in PRINT_FORMATS.items():
		if frappe.db.exists("Print Format", name):
			doc = frappe.get_doc("Print Format", name)
			if doc.module != "Malaysia Workforce" or doc.doc_type != definition["doctype"]:
				frappe.throw(
					_(
						"Print Format {0} is reserved by Malaysia Workforce but already belongs to module {1} "
						"or another DocType. Rename the existing format before installing."
					).format(frappe.bold(name), frappe.bold(doc.module or _("Unknown"))),
					title=_("Reserved Print Format Conflict"),
				)
		else:
			doc = frappe.new_doc("Print Format")
			doc.name = name
			doc.print_format_name = name

		doc.doc_type = definition["doctype"]
		doc.module = "Malaysia Workforce"
		doc.print_format_type = "Jinja"
		doc.custom_format = 1
		doc.disabled = 0
		doc.html = definition["html"]
		if doc.is_new():
			doc.insert(ignore_permissions=True)
		else:
			doc.save(ignore_permissions=True)
