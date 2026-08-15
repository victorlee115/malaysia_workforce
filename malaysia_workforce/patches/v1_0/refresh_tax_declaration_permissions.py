from __future__ import annotations

import frappe

from malaysia_workforce.setup.permissions import _ensure_permission, ensure_employee_self_service_access


TAX_DECLARATION_DOCTYPES = (
	"Malaysia Tax Declaration TP1",
	"Malaysia Previous Employment TP3",
)


def execute():
	"""Add only native Workflow rights omitted by the first lean migration."""
	for doctype in TAX_DECLARATION_DOCTYPES:
		if not frappe.db.exists("DocType", doctype):
			continue
		for role in ("System Manager", "HR Manager"):
			_ensure_permission(
				doctype,
				role,
				rights={"submit": 1, "cancel": 1, "amend": 1},
			)

	# Employee Self Service is a non-standard User Type. Keep its existing
	# narrow document access aligned without touching unrelated role changes.
	ensure_employee_self_service_access()
	frappe.clear_cache()
