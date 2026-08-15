import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from malaysia_workforce.permissions import current_employee


def get_context(context):
	context.show_sidebar = False
	if not frappe.form_dict.is_new:
		return
	employee = current_employee()
	if not employee:
		frappe.throw(_("Your User is not linked to an active Employee."), frappe.PermissionError)
	context.reference_doc = {
		"doctype": "Malaysia Tax Declaration TP1",
		"employee": employee,
		"company": frappe.db.get_value("Employee", employee, "company"),
		"currency": "MYR",
		"tax_year": getdate().year,
		"declaration_date": nowdate(),
	}
