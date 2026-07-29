from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_datetime, getdate, now_datetime

from malaysia_workforce.permissions import can_manage_roster, current_employee, is_roster_admin
from malaysia_workforce.roster.coverage import TimeWindow, validate_non_overlapping
from malaysia_workforce.roster.input_validation import (
	ALLOWED_COMMITMENT_TYPES,
	ALLOWED_PREFERENCES,
	MAX_AVAILABILITY_WINDOWS,
	MAX_EMPLOYEE_NOTES_LENGTH,
	MAX_FLEXIBILITY_MINUTES,
	MAX_ROLE_LENGTH,
)
from malaysia_workforce.utils import combine_date_time, end_after_start, validate_decimal


class RosterApplication(Document):
	def validate(self):
		privileged = is_roster_admin() or can_manage_roster(self.roster)
		if not privileged and self.employee != current_employee():
			frappe.throw(_("You can only create or edit your own roster application."), frappe.PermissionError)
		if not privileged and self.status not in {"Applied", "Withdrawn"}:
			frappe.throw(_("Only a roster manager can change the selection status."), frappe.PermissionError)

		roster = frappe.get_doc("Casual Roster", self.roster)
		self.company = roster.company
		self.application_key = f"{self.roster}|{self.employee}"
		if frappe.db.exists(
			"Roster Application",
			{"application_key": self.application_key, "name": ["!=", self.name]},
		):
			frappe.throw(_("Employee {0} already has an application for this roster.").format(self.employee))
		employee = frappe.db.get_value(
			"Employee", self.employee, ["status", "company", "custom_roster_enabled"], as_dict=True
		)
		if not employee or employee.status != "Active":
			frappe.throw(_("Employee {0} is not active.").format(self.employee))
		if employee.company != roster.company:
			frappe.throw(_("The employee and roster must belong to the same company."))
		if not employee.custom_roster_enabled:
			frappe.throw(_("This employee is not enabled for casual rosters."))

		if not privileged and self.status != "Withdrawn":
			if roster.status != "Open for Applications":
				frappe.throw(_("This roster is not open for applications."))
			if roster.application_opens and now_datetime() < get_datetime(roster.application_opens):
				frappe.throw(_("Applications for this roster have not opened."))
			if roster.application_closes and now_datetime() > get_datetime(roster.application_closes):
				frappe.throw(_("Applications for this roster have closed."))

		minimum = validate_decimal(self.minimum_shift_hours, _("Minimum Shift Hours"), minimum=0)
		maximum = validate_decimal(self.maximum_hours, _("Maximum Hours"), minimum="0.0001")
		if minimum is not None and maximum is not None and maximum < minimum:
			frappe.throw(_("Maximum Hours cannot be below Minimum Shift Hours."))
		self.preferred_role = (self.preferred_role or "").strip() or None
		if self.preferred_role and len(self.preferred_role) > MAX_ROLE_LENGTH:
			frappe.throw(_("Preferred Role cannot exceed {0} characters.").format(MAX_ROLE_LENGTH))
		self.employee_notes = (self.employee_notes or "").strip() or None
		if self.employee_notes and len(self.employee_notes) > MAX_EMPLOYEE_NOTES_LENGTH:
			frappe.throw(_("Employee Notes cannot exceed {0} characters.").format(MAX_EMPLOYEE_NOTES_LENGTH))
		if self.commitment_type not in ALLOWED_COMMITMENT_TYPES:
			frappe.throw(_("Confirmation Preference is not valid."))
		if self.split_shifts_allowed and not cint(
			frappe.db.get_single_value("HR Settings", "allow_multiple_shift_assignments")
		):
			frappe.throw(
				_(
					"Split shifts require 'Allow Multiple Shift Assignments for Same Date' "
					"to be enabled in HR Settings."
				)
			)

		if not self.availability_windows:
			frappe.throw(_("Add at least one availability window."))
		if len(self.availability_windows) > MAX_AVAILABILITY_WINDOWS:
			frappe.throw(_("No more than {0} availability windows are allowed.").format(MAX_AVAILABILITY_WINDOWS))
		by_date: dict = {}
		for row in self.availability_windows:
			if not getdate(roster.start_date) <= getdate(row.work_date) <= getdate(roster.end_date):
				frappe.throw(_("Availability date {0} is outside the roster period.").format(row.work_date))
			start = combine_date_time(row.work_date, row.available_from)
			end = end_after_start(start, combine_date_time(row.work_date, row.available_until))
			if row.preference not in ALLOWED_PREFERENCES:
				frappe.throw(_("Availability preference is not valid."))
			row.preferred_role = (row.preferred_role or "").strip() or None
			if row.preferred_role and len(row.preferred_role) > MAX_ROLE_LENGTH:
				frappe.throw(_("Availability preferred role cannot exceed {0} characters.").format(MAX_ROLE_LENGTH))
			row_minimum = validate_decimal(row.minimum_assignment_hours, _("Minimum Assignment Hours"), minimum="0.0001")
			row_maximum = validate_decimal(row.maximum_assignment_hours, _("Maximum Assignment Hours"), minimum="0.0001")
			if row_minimum is not None and row_maximum is not None and row_minimum > row_maximum:
				frappe.throw(_("Minimum assignment hours cannot exceed maximum assignment hours."))
			for fieldname in ("can_start_earlier_minutes", "can_finish_later_minutes"):
				value = validate_decimal(
					row.get(fieldname), self.meta.get_label(fieldname) or fieldname, minimum=0, maximum=MAX_FLEXIBILITY_MINUTES
				)
				if value is not None and value != int(value):
					frappe.throw(_("Flexibility minutes must be a whole number."))
			if not self._overlaps_coverage(roster, start, end):
				frappe.throw(
					_("Availability {0} {1}–{2} does not overlap any roster coverage requirement.").format(
						row.work_date, row.available_from, row.available_until
					)
				)
			by_date.setdefault(getdate(row.work_date), []).append(TimeWindow(start, end, row.preference))
		for windows in by_date.values():
			try:
				validate_non_overlapping(windows)
			except ValueError as exc:
				frappe.throw(_(str(exc)))
		self.applied_on = self.applied_on or now_datetime()

	@staticmethod
	def _overlaps_coverage(roster, start, end) -> bool:
		for requirement in roster.coverage_requirements:
			requirement_start = combine_date_time(requirement.work_date, requirement.start_time)
			requirement_end = end_after_start(
				requirement_start,
				combine_date_time(requirement.work_date, requirement.end_time),
			)
			if start < requirement_end and requirement_start < end:
				return True
		return False

	def on_update(self):
		if self.status == "Applied":
			frappe.publish_realtime(
				"malaysia_workforce:roster_application",
				{"roster": self.roster, "application": self.name},
				after_commit=True,
			)
