import frappe
from frappe import _
from frappe.model.document import Document

from malaysia_workforce.utils import validate_decimal


class MalaysiaWorkforceSettings(Document):
	def validate(self):
		slot_minutes = validate_decimal(self.roster_slot_minutes, _("Roster Slot Minutes"), minimum=1, allow_blank=False)
		minimum_shift = validate_decimal(self.minimum_shift_minutes, _("Default Minimum Shift Minutes"), minimum=1, allow_blank=False)
		validate_decimal(self.minimum_hourly_rate, _("Configured Minimum Hourly Rate"), minimum="0.01", allow_blank=False)
		validate_decimal(self.application_reminder_hours, _("Application Reminder Hours"), minimum=0)
		validate_decimal(self.checkin_grace_before_minutes, _("Check-in Grace Before Minutes"), minimum=0)
		validate_decimal(self.checkout_grace_after_minutes, _("Check-out Grace After Minutes"), minimum=0)
		validate_decimal(self.auto_approve_time_tolerance_minutes, _("Auto-approve Time Tolerance Minutes"), minimum=0)
		if int(slot_minutes) != slot_minutes or 1440 % int(slot_minutes):
			frappe.throw(_("Roster Slot Minutes must be a positive whole-number divisor of 1,440."))
		if minimum_shift < slot_minutes:
			frappe.throw(_("Default minimum shift cannot be shorter than one roster slot."))
