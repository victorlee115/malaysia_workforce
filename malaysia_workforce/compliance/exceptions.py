from __future__ import annotations

import hashlib

import frappe
from frappe import _
from frappe.utils import now_datetime
from frappe.utils.user import get_users_with_role

from malaysia_workforce.utils import ensure_private_file


def _accountable_user() -> str:
	for role in ("Malaysia HR Manager", "HR Manager", "System Manager"):
		users = sorted(
			user
			for user in get_users_with_role(role)
			if user not in {"Administrator", "Guest"} and frappe.db.get_value("User", user, "enabled")
		)
		if users:
			return users[0]
	return "Administrator"


def create_assigned_exception(
	*,
	code: str,
	description: str,
	reference_type: str | None = None,
	reference_name: str | None = None,
	due_date=None,
	allocated_to: str | None = None,
) -> str:
	"""Create one standard ToDo per immutable exception content hash."""
	payload = "|".join((code, reference_type or "", reference_name or "", description))
	digest = hashlib.sha256(payload.encode()).hexdigest()
	existing = frappe.db.get_value(
		"ToDo",
		{"custom_malaysia_content_hash": digest, "status": "Open"},
		"name",
	)
	if existing:
		return existing
	doc = frappe.get_doc(
		{
			"doctype": "ToDo",
			"allocated_to": allocated_to or _accountable_user(),
			"description": description,
			"reference_type": reference_type,
			"reference_name": reference_name,
			"date": due_date,
			"priority": "High",
			"custom_malaysia_exception_code": code,
			"custom_malaysia_content_hash": digest,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def validate_exception_todo(doc, method=None) -> None:
	"""Require accountable, evidenced and immutable exception resolution."""
	if not getattr(doc, "custom_malaysia_exception_code", None):
		return
	before = doc.get_doc_before_save()
	if before and before.custom_malaysia_resolution_hash:
		protected = (
			"status",
			"allocated_to",
			"description",
			"reference_type",
			"reference_name",
			"custom_malaysia_exception_code",
			"custom_malaysia_content_hash",
			"custom_malaysia_resolution_evidence",
			"custom_malaysia_resolved_by",
			"custom_malaysia_resolved_on",
			"custom_malaysia_resolution_hash",
		)
		if any(str(before.get(fieldname) or "") != str(doc.get(fieldname) or "") for fieldname in protected):
			frappe.throw(_("A resolved Malaysia exception is immutable. Create a new assigned exception."))
		return
	if doc.status not in {"Closed", "Cancelled"}:
		return
	if doc.allocated_to != frappe.session.user:
		frappe.throw(_("Only the exception's accountable assignee may resolve it."))
	if not doc.custom_malaysia_resolution_evidence:
		frappe.throw(_("Attach resolution evidence before closing this Malaysia exception."))
	doc.custom_malaysia_resolution_evidence = ensure_private_file(
		doc.custom_malaysia_resolution_evidence,
		_("Exception resolution evidence"),
	)
	doc.custom_malaysia_resolved_by = frappe.session.user
	doc.custom_malaysia_resolved_on = now_datetime()
	payload = "|".join(
		(
			doc.custom_malaysia_content_hash or "",
			doc.status,
			doc.custom_malaysia_resolution_evidence,
			doc.custom_malaysia_resolved_by,
			str(doc.custom_malaysia_resolved_on),
		)
	)
	doc.custom_malaysia_resolution_hash = hashlib.sha256(payload.encode()).hexdigest()
