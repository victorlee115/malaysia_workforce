from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime


def validate_staffing_priority(doc, method=None):
	priority = getattr(doc, "custom_staffing_priority", None) or "Standard"
	if priority not in {"Priority", "Preferred", "Standard"}:
		frappe.throw(_("Staffing Priority must be Priority, Preferred, or Standard."))
	before = doc.get_doc_before_save()
	changed = bool(before) and any(
		str(before.get(fieldname) or "") != str(doc.get(fieldname) or "")
		for fieldname in (
			"custom_staffing_priority",
			"custom_staffing_priority_reason",
			"custom_staffing_priority_effective_from",
			"custom_staffing_priority_expires_on",
		)
	)
	changed = changed or (not before and priority != "Standard")
	if changed and not set(frappe.get_roles()) & {"Outlet Manager", "HR Manager", "Malaysia HR Manager", "System Manager"}:
		frappe.throw(_("Only an authorised staffing manager may change Staffing Priority."), frappe.PermissionError)
	if priority == "Standard":
		if changed:
			doc.custom_staffing_priority_reason = ""
			doc.custom_staffing_priority_effective_from = None
			doc.custom_staffing_priority_expires_on = None
			doc.custom_staffing_priority_reviewed_by = frappe.session.user
			doc.custom_staffing_priority_reviewed_on = now_datetime()
		return
	if not (doc.custom_staffing_priority_reason or "").strip() or not doc.custom_staffing_priority_effective_from or not doc.custom_staffing_priority_expires_on:
		frappe.throw(_("A non-standard staffing priority requires a reason, effective date, and expiry date."))
	if getdate(doc.custom_staffing_priority_effective_from) > getdate(doc.custom_staffing_priority_expires_on):
		frappe.throw(_("Staffing Priority effective date cannot be after its expiry."))
	if getdate(doc.custom_staffing_priority_expires_on) < getdate():
		frappe.throw(_("Staffing Priority expiry must not be in the past."))
	if changed:
		doc.custom_staffing_priority_reviewed_by = frappe.session.user
		doc.custom_staffing_priority_reviewed_on = now_datetime()
