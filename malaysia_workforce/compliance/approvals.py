from __future__ import annotations

import frappe
from frappe import _


def prevent_self_approval(doc, method=None) -> None:
	"""Block an employee from recording approval of their own HRMS input.

	Standard submission by an employee remains allowed; this guard only applies
	when the standard document has actually entered an approved state.
	"""
	status = str(getattr(doc, "approval_status", None) or getattr(doc, "status", None) or "")
	if status not in {"Approved", "Sanctioned"}:
		return
	employee = getattr(doc, "employee", None)
	if not employee:
		return
	employee_user = frappe.db.get_value("Employee", employee, "user_id")
	if employee_user and employee_user == frappe.session.user:
		frappe.throw(_("You cannot approve your own attendance or claim input."), frappe.PermissionError)
