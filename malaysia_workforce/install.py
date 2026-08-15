from __future__ import annotations

import frappe
from frappe import _

from malaysia_workforce.patches.v1_0.retire_parallel_hr_roles import require_reviewed_role_mapping
from malaysia_workforce.setup.custom_fields import create_custom_fields, remove_legacy_custom_fields
from malaysia_workforce.setup.master_data import create_master_data
from malaysia_workforce.setup.permissions import ensure_standard_record_permissions
from malaysia_workforce.setup.print_formats import ensure_salary_slip_print_format
from malaysia_workforce.setup.workflows import ensure_tax_declaration_workflows

SUPPORTED_MAJOR = 16
LEGACY_DOCTYPES = (
	"Casual Availability", "Cafe Coverage Template", "Cafe Staffing Plan",
	"Malaysia Payroll Run", "Malaysia Employee Profile", "Employee Work Agreement",
	"Shift Work Record", "Monthly Statutory Accumulator", "Statutory Submission",
)


def before_install():
	for app in ("erpnext", "hrms"):
		if app not in frappe.get_installed_apps():
			frappe.throw(_("Malaysia Payroll requires ERPNext and Frappe HR to be installed first."))
	if int(frappe.__version__.split(".")[0]) != SUPPORTED_MAJOR:
		frappe.throw(_("Malaysia Payroll supports Frappe v16 only."))


def after_install():
	create_custom_fields()
	ensure_standard_record_permissions()
	create_master_data()
	ensure_salary_slip_print_format()
	ensure_tax_declaration_workflows()
	frappe.clear_cache()


def before_migrate():
	require_reviewed_role_mapping()
	occupied = []
	for doctype in LEGACY_DOCTYPES:
		if frappe.db.exists("DocType", doctype) and frappe.db.count(doctype):
			occupied.append(f"{doctype} ({frappe.db.count(doctype)})")
	if occupied:
		frappe.throw(_("Lean Malaysia Payroll cannot remove legacy operational records automatically. "
			"Archive or migrate these records first: {0}").format(", ".join(occupied)))


def after_migrate():
	create_custom_fields()
	remove_legacy_custom_fields()
	ensure_standard_record_permissions()
	create_master_data()
	ensure_salary_slip_print_format()
	ensure_tax_declaration_workflows()
	frappe.clear_cache()
