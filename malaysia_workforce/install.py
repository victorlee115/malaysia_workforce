from __future__ import annotations

import frappe
from frappe import _

from malaysia_workforce.setup.custom_fields import create_custom_fields
from malaysia_workforce.setup.master_data import create_master_data

SUPPORTED_MAJOR = 16


def before_install():
	for app in ("erpnext", "hrms"):
		if app not in frappe.get_installed_apps():
			frappe.throw(_("Malaysia Workforce requires ERPNext and Frappe HR to be installed first."))
	major = int(frappe.__version__.split(".")[0])
	if major != SUPPORTED_MAJOR:
		frappe.throw(_("Malaysia Workforce 1.0.0-rc.3 supports Frappe v16 only. Detected v{0}.").format(major))


def after_install():
	create_custom_fields()
	create_master_data()
	frappe.clear_cache()


def after_migrate():
	create_custom_fields()
	create_master_data()
	frappe.clear_cache()


def before_uninstall():
	# Custom fields are intentionally retained to avoid destructive data loss.
	# Administrators may remove them manually after exporting all statutory records.
	pass
