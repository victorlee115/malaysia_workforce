from __future__ import annotations

import frappe


def execute():
	"""Remove the obsolete workspace shipped by the pre-lean application."""
	if frappe.db.exists("Workspace", "Malaysia Workforce"):
		frappe.delete_doc("Workspace", "Malaysia Workforce", force=True, ignore_permissions=True)
	frappe.clear_cache()
