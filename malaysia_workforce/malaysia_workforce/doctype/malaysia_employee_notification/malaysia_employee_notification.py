import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, getdate

from malaysia_workforce.utils import ensure_private_file

FROZEN_STATUSES = {"Submitted", "Accepted"}


class MalaysiaEmployeeNotification(Document):
	def validate(self):
		expected_event = {"CP22": "Commencement", "CP21": "Departure"}.get(self.form_type)
		if self.form_type not in {"CP21", "CP22", "CP22A"}:
			frappe.throw(_("Only CP21, CP22 and private-sector CP22A are supported."))
		if expected_event and self.event_type != expected_event:
			frappe.throw(_("{0} must use the {1} event.").format(self.form_type, expected_event))
		if self.form_type == "CP22A" and self.event_type not in {"Cessation", "Death"}:
			frappe.throw(_("CP22A must use a Cessation or Death event."))
		trigger = getdate(self.trigger_date)
		if self.form_type == "CP22":
			expected_due = add_days(trigger, 30)
		elif self.form_type == "CP22A" and self.event_type == "Death":
			if not self.death_date:
				frappe.throw(_("Date of Death is required for a death notification."))
			expected_due = add_days(getdate(self.death_date), 30)
		elif self.form_type == "CP22A":
			if not self.cessation_date:
				frappe.throw(_("Cessation Date is required for CP22A."))
			expected_due = add_days(getdate(self.cessation_date), -30)
		else:
			if not self.departure_date:
				frappe.throw(_("Departure Date is required for CP21."))
			expected_due = add_days(getdate(self.departure_date), -30)
		self.due_date = expected_due
		if self.withholding_required and not self.withholding_until:
			frappe.throw(_("Withhold Until is required when monies must be withheld."))
		if self.status in FROZEN_STATUSES:
			if not self.submission_reference or not self.submitted_on:
				frappe.throw(_("Submission Reference and Submitted On are required after submission."))
			self.acknowledgement = ensure_private_file(
				self.acknowledgement,
				_("Employee notification submission acknowledgement"),
			)
		before = self.get_doc_before_save()
		if before and before.status in FROZEN_STATUSES:
			protected = {
				key: value
				for key, value in before.as_dict().items()
				if key not in {"status", "payload_snapshot", "modified", "modified_by", "_comments"}
			}
			current = {
				key: value
				for key, value in self.as_dict().items()
				if key not in {"status", "payload_snapshot", "modified", "modified_by", "_comments"}
			}
			if json.dumps(protected, default=str, sort_keys=True) != json.dumps(current, default=str, sort_keys=True):
				frappe.throw(_("Submitted notification data is immutable. Create a corrected record."))
		self.payload_snapshot = json.dumps({key: value for key, value in self.as_dict().items() if key not in {"payload_snapshot", "_comments"}}, default=str, sort_keys=True)

	def on_trash(self):
		if self.status != "Draft":
			frappe.throw(_("Only draft employee notifications may be deleted."))
