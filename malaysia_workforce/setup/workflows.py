from __future__ import annotations

import frappe


WORKFLOW_NAME = "Employee Tax Declaration Review"
DOCUMENT_TYPES = ("Malaysia Tax Declaration TP1", "Malaysia Previous Employment TP3")


def ensure_tax_declaration_workflows() -> None:
	"""Install the same small native review workflow on TP1 and TP3."""
	for state, style in (("Draft", ""), ("Pending Review", "Warning"), ("Approved", "Success")):
		if not frappe.db.exists("Workflow State", state):
			frappe.get_doc(
				{"doctype": "Workflow State", "workflow_state_name": state, "style": style}
			).insert(ignore_permissions=True)
	for action in ("Send for Review", "Approve", "Return"):
		if not frappe.db.exists("Workflow Action Master", action):
			frappe.get_doc(
				{"doctype": "Workflow Action Master", "workflow_action_name": action}
			).insert(ignore_permissions=True)

	for doctype in DOCUMENT_TYPES:
		name = f"{WORKFLOW_NAME} - {doctype.rsplit(' ', 1)[-1]}"
		doc = frappe.get_doc("Workflow", name) if frappe.db.exists("Workflow", name) else frappe.new_doc("Workflow")
		doc.workflow_name = name
		doc.document_type = doctype
		doc.is_active = 1
		doc.override_status = 0
		doc.send_email_alert = 0
		doc.enable_action_confirmation = 1
		doc.workflow_state_field = "workflow_state"
		doc.set(
			"states",
			[
				{"state": "Draft", "doc_status": "0", "allow_edit": "Employee Self Service"},
				{"state": "Pending Review", "doc_status": "0", "allow_edit": "HR Manager"},
				{"state": "Approved", "doc_status": "1", "allow_edit": "HR Manager"},
			],
		)
		doc.set(
			"transitions",
			[
				{
					"state": "Draft",
					"action": "Send for Review",
					"next_state": "Pending Review",
					"allowed": "Employee Self Service",
					"allow_self_approval": 1,
				},
				{
					"state": "Pending Review",
					"action": "Approve",
					"next_state": "Approved",
					"allowed": "HR Manager",
					"allow_self_approval": 0,
				},
				{
					"state": "Pending Review",
					"action": "Return",
					"next_state": "Draft",
					"allowed": "HR Manager",
					"allow_self_approval": 0,
				},
			],
		)
		if doc.is_new():
			doc.insert(ignore_permissions=True)
		else:
			doc.save(ignore_permissions=True)
