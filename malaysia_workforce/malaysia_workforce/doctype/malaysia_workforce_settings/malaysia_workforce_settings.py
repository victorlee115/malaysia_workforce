import frappe
from frappe import _
from frappe.model.document import Document

from malaysia_workforce.utils import validate_decimal


class MalaysiaWorkforceSettings(Document):
	def validate(self):
		slot_minutes = validate_decimal(self.staffing_slot_minutes, _("Staffing Time Step"), minimum=1, allow_blank=False)
		preferred = validate_decimal(self.preferred_minimum_shift_hours, _("Preferred Minimum Shift Hours"), minimum="0.5", allow_blank=False)
		normal = validate_decimal(self.normal_minimum_shift_hours, _("Normal Minimum Shift Hours"), minimum="0.5", allow_blank=False)
		maximum = validate_decimal(self.maximum_recommended_shift_hours, _("Maximum Recommended Shift Hours"), minimum="0.5", allow_blank=False)
		validate_decimal(self.availability_reminder_hours, _("Availability Reminder Hours"), minimum=0)
		validate_decimal(self.availability_lead_days, _("Availability Lead Days"), minimum=1)
		validate_decimal(self.availability_close_days, _("Availability Close Days"), minimum=1)
		validate_decimal(self.approval_lead_days, _("Approval Lead Days"), minimum=1)
		validate_decimal(self.checkin_grace_before_minutes, _("Check-in Grace Before Minutes"), minimum=0)
		validate_decimal(self.checkout_grace_after_minutes, _("Check-out Grace After Minutes"), minimum=0)
		validate_decimal(self.auto_approve_time_tolerance_minutes, _("Auto-approve Time Tolerance Minutes"), minimum=0)
		if int(slot_minutes) != slot_minutes or 1440 % int(slot_minutes):
			frappe.throw(_("Staffing Time Step must be a positive whole-number divisor of 1,440."))
		if not normal <= preferred <= maximum:
			frappe.throw(_("Normal minimum hours must not exceed preferred hours, and preferred hours must not exceed the maximum."))
		if self.flexible_shift_template and frappe.db.get_value("Shift Type", self.flexible_shift_template, "custom_malaysia_managed_shift"):
			frappe.throw(_("Base Casual Shift Type must be a manually configured HRMS Shift Type, not an app-managed flexible type."))
		if self.auto_create_employer_contribution_journal or self.auto_generate_statutory_files_on_final_run:
			companies = frappe.get_all(
				"Company", filters={"custom_enable_malaysia_payroll": 1}, pluck="name"
			)
			if not companies:
				frappe.throw(_("Configure a Malaysia payroll Company before enabling automatic production artifacts."))
			from malaysia_workforce.compliance.scope import assert_company_activation

			for company in companies:
				assert_company_activation(company)
