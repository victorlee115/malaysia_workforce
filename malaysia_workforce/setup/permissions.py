from __future__ import annotations

import frappe
from frappe.permissions import add_permission, setup_custom_perms


AUDITOR_SOURCE_DOCTYPES = (
	"Company",
	"Employee",
	"Contract",
	"Salary Component",
	"Salary Structure",
	"Salary Structure Assignment",
	"Additional Salary",
	"Overtime Slip",
	"Payroll Entry",
	"Salary Slip",
)

ESS_DOCUMENT_ACCESS = {
	"Malaysia Tax Declaration TP1": {"read", "write", "create", "delete", "print"},
	"Malaysia Previous Employment TP3": {"read", "write", "create", "delete", "print"},
}


def ensure_standard_record_permissions() -> None:
	"""Add the minimum localization access missing from standard role matrices."""
	ensure_employee_self_service_access()
	setup_custom_perms("Employee")
	_ensure_permission("Employee", "HR Manager", permlevel=1, rights={"read": 1, "write": 1})
	_ensure_permission("Employee", "Auditor", permlevel=1, rights={"read": 1, "export": 1})

	for doctype in AUDITOR_SOURCE_DOCTYPES:
		if not frappe.db.exists("DocType", doctype):
			continue
		setup_custom_perms(doctype)
		_ensure_permission(
			doctype,
			"Auditor",
			rights={"read": 1, "select": 1, "report": 1, "export": 1, "print": 1},
		)
		frappe.clear_cache(doctype=doctype)

	frappe.clear_cache(doctype="Employee")


def ensure_employee_self_service_access() -> None:
	"""Extend HRMS's native employee user type; never create a parallel role."""
	if not frappe.db.exists("User Type", "Employee Self Service"):
		return

	# HRMS's non-standard User Type updater manages Custom DocPerm rows. App
	# DocType JSON is initially represented by standard DocPerm rows, so make a
	# custom copy before the updater tries to mutate it.
	for doctype in ESS_DOCUMENT_ACCESS:
		if frappe.db.exists("DocType", doctype):
			setup_custom_perms(doctype)

	user_type = frappe.get_doc("User Type", "Employee Self Service")
	rows = {row.document_type: row for row in user_type.user_doctypes}
	changed = False
	for doctype, rights in ESS_DOCUMENT_ACCESS.items():
		if not frappe.db.exists("DocType", doctype):
			continue
		row = rows.get(doctype)
		if not row:
			row = user_type.append("user_doctypes", {"document_type": doctype})
			rows[doctype] = row
			changed = True
		for right in rights:
			if not row.get(right):
				row.set(right, 1)
				changed = True

	if changed:
		user_type.flags.ignore_links = True
		user_type.save(ignore_permissions=True)
	frappe.clear_cache()


def _ensure_permission(doctype: str, role: str, *, permlevel: int = 0, rights: dict) -> None:
	name = frappe.db.get_value(
		"Custom DocPerm",
		{"parent": doctype, "role": role, "permlevel": permlevel, "if_owner": 0},
		"name",
	)
	if not name:
		name = add_permission(doctype, role, permlevel, "read")
	if name:
		frappe.db.set_value("Custom DocPerm", name, rights, update_modified=False)
