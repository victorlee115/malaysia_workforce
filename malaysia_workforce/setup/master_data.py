from __future__ import annotations

import frappe
from frappe import _


COMPONENTS = {
	"EPF Employee": {"abbr": "EPFE", "type": "Deduction"},
	"SOCSO Employee": {"abbr": "SOC", "type": "Deduction"},
	"SKBBK Employee": {"abbr": "SKB", "type": "Deduction"},
	"EIS Employee": {"abbr": "EIS", "type": "Deduction"},
	"PCB": {"abbr": "PCB", "type": "Deduction"},
	"CP38": {"abbr": "CP38", "type": "Deduction"},
	"Zakat": {"abbr": "ZAK", "type": "Deduction"},
}


def create_master_data():
	for name, values in COMPONENTS.items():
		_create_component(name, values)


def _create_component(name: str, values: dict):
	if frappe.db.exists("Salary Component", name):
		doc = frappe.get_doc("Salary Component", name)
		if doc.type != values["type"]:
			frappe.throw(
				_("Salary Component {0} exists with the wrong type. Rename it before installing Malaysia Payroll.").format(
					frappe.bold(name)
				)
			)
	else:
		doc = frappe.new_doc("Salary Component")
		doc.salary_component = name
		doc.salary_component_abbr = values["abbr"]
		doc.type = values["type"]
		doc.remove_if_zero_valued = 1
		doc.depends_on_payment_days = 0
	if values["type"] == "Earning":
		doc.custom_include_in_epf_wages = values.get("epf", 0)
		doc.custom_include_in_socso_wages = values.get("socso", 0)
		doc.custom_include_in_eis_wages = values.get("eis", 0)
		doc.custom_pcb_treatment = values.get("pcb")
		doc.custom_include_in_ordinary_rate = values.get("ordinary", 0)
	if doc.is_new():
		doc.insert(ignore_permissions=True)
	else:
		# Upgrade only the Malaysia treatment owned by this app. Existing accounts,
		# formulas and other administrator configuration remain untouched.
		doc.save(ignore_permissions=True)
