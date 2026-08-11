from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime

from malaysia_workforce.utils import ensure_private_file


def validate_privacy_acknowledgement(doc, method=None) -> None:
	"""Version employee acknowledgement evidence on the standard Employee record."""
	if not getattr(doc, "company", None) or not frappe.db.get_value(
		"Company", doc.company, "custom_enable_malaysia_payroll"
	):
		return
	before = doc.get_doc_before_save()
	evidence = getattr(doc, "custom_malaysia_privacy_acknowledgement", None)
	previous_evidence = getattr(before, "custom_malaysia_privacy_acknowledgement", None) if before else None
	protected = (
		"custom_malaysia_privacy_notice_version",
		"custom_malaysia_privacy_acknowledged_by",
		"custom_malaysia_privacy_acknowledged_on",
	)
	if before and evidence == previous_evidence:
		for fieldname in protected:
			if str(before.get(fieldname) or "") != str(doc.get(fieldname) or ""):
				frappe.throw(_("Privacy acknowledgement audit fields are immutable."))
	elif evidence:
		if frappe.session.user == "Guest":
			frappe.throw(_("Sign in before recording a privacy acknowledgement."), frappe.PermissionError)
		own_employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
		roles = set(frappe.get_roles())
		if own_employee != doc.name and not roles.intersection(
			{"HR Manager", "Malaysia HR Manager", "System Manager"}
		):
			frappe.throw(_("Only the employee or an HR Manager recording signed evidence may acknowledge this notice."))
		notice_version = frappe.db.get_value("Company", doc.company, "custom_malaysia_privacy_notice_version")
		if not notice_version:
			frappe.throw(_("Set the Company's Malaysia Privacy Notice Version first."))
		evidence = ensure_private_file(evidence, _("Privacy acknowledgement evidence"))
		doc.custom_malaysia_privacy_acknowledgement = evidence
		doc.custom_malaysia_privacy_notice_version = notice_version
		doc.custom_malaysia_privacy_acknowledged_by = frappe.session.user
		doc.custom_malaysia_privacy_acknowledged_on = now_datetime()
	elif before and previous_evidence:
		frappe.throw(_("A recorded privacy acknowledgement cannot be removed; attach evidence for the new notice version."))

	production = frappe.db.get_value("Company", doc.company, "custom_malaysia_production_activated")
	if getattr(doc, "status", None) == "Active" and production:
		current_version = frappe.db.get_value("Company", doc.company, "custom_malaysia_privacy_notice_version")
		if not evidence or doc.custom_malaysia_privacy_notice_version != current_version:
			frappe.throw(_("A current Malaysia privacy-notice acknowledgement is required for an active Employee."))
