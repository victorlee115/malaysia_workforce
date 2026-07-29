from __future__ import annotations

from datetime import timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, getdate, now_datetime

from malaysia_workforce.data_access import get_work_agreement
from malaysia_workforce.roster.hour_limits import enforce_roster_hour_limits
from malaysia_workforce.utils import combine_date_time, end_after_start, validate_decimal


class RosterSelection(Document):
	def validate(self):
		application = frappe.get_doc("Roster Application", self.application)
		if application.roster != self.roster or application.employee != self.employee:
			frappe.throw(_("Roster Selection does not match the selected application."))
		if application.status not in {"Applied", "Standby", "Selected"}:
			frappe.throw(_("Application {0} is not eligible for selection.").format(application.name))

		roster = frappe.get_doc("Casual Roster", self.roster)
		if roster.status in {"Draft", "Completed", "Payroll Ready", "Closed"}:
			frappe.throw(_("Workers cannot be selected while the roster is in status {0}.").format(roster.status))
		if application.company != roster.company:
			frappe.throw(_("The application and roster must belong to the same company."))
		self.company = roster.company

		employee = frappe.db.get_value(
			"Employee", self.employee, ["status", "company"], as_dict=True
		)
		if not employee or employee.status != "Active":
			frappe.throw(_("Employee {0} is not active.").format(self.employee))
		if employee.company != roster.company:
			frappe.throw(_("The employee and roster must belong to the same company."))

		start = combine_date_time(self.work_date, self.selected_from)
		end = end_after_start(start, combine_date_time(self.work_date, self.selected_until))
		if end <= start:
			frappe.throw(_("Selected Until must be after Selected From."))
		if not getdate(roster.start_date) <= getdate(self.work_date) <= getdate(roster.end_date):
			frappe.throw(_("Selected date is outside the roster period."))

		requirement = self._get_requirement(roster, start, end)
		from malaysia_workforce.roster.skills import employee_has_required_skill

		if requirement.required_skill and not employee_has_required_skill(
			self.employee, requirement.required_skill
		):
			frappe.throw(
				_("Employee {0} does not have the required skill {1}.").format(
					self.employee, requirement.required_skill
				)
			)
		self.coverage_requirement_idx = requirement.idx
		if not self.assigned_role:
			self.assigned_role = requirement.role
		self.assigned_role = (self.assigned_role or "").strip()
		if len(self.assigned_role) > 140:
			frappe.throw(_("Assigned Role cannot exceed 140 characters."))
		if self.assigned_role.casefold() != (requirement.role or "").strip().casefold():
			frappe.throw(
				_("Assigned Role must match coverage row {0}: {1}.").format(requirement.idx, requirement.role)
			)
		self.shift_location = self.shift_location or requirement.shift_location or roster.default_shift_location
		self.cost_center = self.cost_center or requirement.cost_center
		self.project = self.project or requirement.project or roster.project
		self._validate_accounting_dimensions()

		agreement = get_work_agreement(self.employee, self.work_date, required=True)
		if agreement.get("company") and agreement.get("company") != roster.company:
			frappe.throw(_("The employee work agreement belongs to a different company."))
		if not self.hourly_rate:
			self.hourly_rate = requirement.hourly_rate or agreement.get("base_hourly_rate") or 0

		settings = frappe.get_cached_doc("Malaysia Workforce Settings")
		duration_hours = (end - start).total_seconds() / 3600
		matched_window = self._matching_availability_window(application, start, end)
		minimum_hours = max(
			float(application.minimum_shift_hours or 0),
			float(settings.minimum_shift_minutes or 0) / 60,
			float(matched_window.minimum_assignment_hours or 0) if matched_window else 0,
		)
		if duration_hours < minimum_hours:
			frappe.throw(
				_("Selected duration is {0:.2f} hours; the minimum accepted duration is {1:.2f} hours.").format(
					duration_hours, minimum_hours
				)
			)
		if matched_window and matched_window.maximum_assignment_hours:
			if duration_hours > float(matched_window.maximum_assignment_hours) + 1e-9:
				frappe.throw(
					_("Selected duration exceeds the maximum accepted for this availability window ({0:.2f} hours).").format(
						float(matched_window.maximum_assignment_hours)
					)
				)
		rate = validate_decimal(self.hourly_rate, _("Hourly Rate"), minimum="0.01", allow_blank=False)
		if (
			settings.minimum_wage_effective_from
			and getdate(self.work_date) >= getdate(settings.minimum_wage_effective_from)
			and rate < validate_decimal(settings.minimum_hourly_rate, _("Minimum Hourly Rate"), minimum=0, allow_blank=False)
		):
			frappe.throw(
				_("Hourly rate RM {0:.2f} is below the configured minimum of RM {1:.2f}.").format(
					float(rate), float(settings.minimum_hourly_rate or 0)
				)
			)
		if not matched_window and not self.outside_availability_override:
			frappe.throw(
				_(
					"The selected hours are outside the employee's submitted availability and declared flexibility. "
					"Enable the override and record a reason to continue."
				)
			)
		self.override_reason = (self.override_reason or "").strip()
		if self.outside_availability_override and not self.override_reason:
			frappe.throw(_("Override Reason is required when assigning outside availability."))
		if len(self.override_reason) > 1000:
			frappe.throw(_("Override Reason cannot exceed 1000 characters."))

		existing_for_application = frappe.get_all(
			"Roster Selection",
			filters={
				"application": self.application,
				"docstatus": ["<", 2],
				"status": ["!=", "Declined"],
				"name": ["!=", self.name],
			},
			fields=["work_date", "selected_from", "selected_until"],
			limit_page_length=500,
		)
		allocated = 0.0
		for item in existing_for_application:
			item_start = combine_date_time(item.work_date, item.selected_from)
			item_end = end_after_start(item_start, combine_date_time(item.work_date, item.selected_until))
			allocated += (item_end - item_start).total_seconds() / 3600
		if application.maximum_hours and allocated + duration_hours > float(application.maximum_hours) + 1e-9:
			frappe.throw(_("This selection would exceed the employee's maximum hours for the roster."))

		week_start = getdate(self.work_date) - timedelta(days=getdate(self.work_date).weekday())
		week_end = week_start + timedelta(days=6)
		existing_week_intervals = []
		for item in frappe.get_all(
			"Roster Selection",
			filters={
				"employee": self.employee,
				"work_date": ["between", [week_start, week_end]],
				"docstatus": ["<", 2],
				"status": ["!=", "Declined"],
				"name": ["!=", self.name],
			},
			fields=["work_date", "selected_from", "selected_until"],
			limit_page_length=1000,
		):
			item_start = combine_date_time(item.work_date, item.selected_from)
			item_end = end_after_start(item_start, combine_date_time(item.work_date, item.selected_until))
			existing_week_intervals.append((item_start, item_end))

		from malaysia_workforce.roster.services import get_standard_shift_assignment_intervals

		allow_multiple_same_date = cint(
			frappe.db.get_single_value("HR Settings", "allow_multiple_shift_assignments")
		)
		same_date_shift_assignments = []
		for row in frappe.get_all(
			"Shift Assignment",
			filters={
				"employee": self.employee,
				"docstatus": 1,
				"status": "Active",
				"start_date": ["<=", self.work_date],
			},
			fields=["name", "start_date", "end_date", "custom_roster_selection"],
			limit_page_length=1000,
		):
			if row.custom_roster_selection == self.name:
				continue
			if getdate(row.end_date or "2999-12-31") >= getdate(self.work_date):
				same_date_shift_assignments.append(row)
		if same_date_shift_assignments and not allow_multiple_same_date:
			frappe.throw(
				_(
					"Employee {0} already has a Shift Assignment covering {1}. Enable "
					"'Allow Multiple Shift Assignments for Same Date' in HR Settings before "
					"using split shifts."
				).format(self.employee, self.work_date)
			)

		standard_intervals = get_standard_shift_assignment_intervals(self.employee, week_start, week_end)
		for interval in standard_intervals:
			existing_week_intervals.append((interval["start"], interval["end"]))
			if start < interval["end"] and interval["start"] < end:
				frappe.throw(
					_("This assignment overlaps standard Shift Assignment {0}.").format(interval["name"])
				)
		try:
			enforce_roster_hour_limits(
				new_start=start,
				new_end=end,
				existing_intervals=existing_week_intervals,
				maximum_daily_hours=agreement.get("maximum_daily_hours") or 0,
				maximum_weekly_hours=agreement.get("maximum_weekly_hours") or 0,
			)
		except ValueError as exc:
			frappe.throw(_(str(exc)))
		if existing_for_application and not application.split_shifts_allowed:
			for item in existing_for_application:
				if getdate(item.work_date) == getdate(self.work_date):
					frappe.throw(_("The employee did not agree to split shifts on the same day."))

		for other in frappe.get_all(
			"Roster Selection",
			filters={
				"employee": self.employee,
				"work_date": self.work_date,
				"docstatus": ["<", 2],
				"status": ["!=", "Declined"],
				"name": ["!=", self.name],
			},
			fields=["name", "selected_from", "selected_until"],
			limit_page_length=500,
		):
			other_start = combine_date_time(self.work_date, other.selected_from)
			other_end = end_after_start(other_start, combine_date_time(self.work_date, other.selected_until))
			if start < other_end and other_start < end:
				frappe.throw(_("This assignment overlaps Roster Selection {0}.").format(other.name))

		self._set_confirmation_status(application)
		self._warn_if_requirement_is_fully_staffed(requirement, start, end)

	def _matching_availability_window(self, application, start, end):
		for window in application.availability_windows:
			window_start = combine_date_time(window.work_date, window.available_from)
			window_end = end_after_start(window_start, combine_date_time(window.work_date, window.available_until))
			flexible_start = window_start - timedelta(minutes=int(window.can_start_earlier_minutes or 0))
			flexible_end = window_end + timedelta(minutes=int(window.can_finish_later_minutes or 0))
			if flexible_start <= start and end <= flexible_end:
				return window
		return None

	def _set_confirmation_status(self, application):
		before = self.get_doc_before_save()
		sensitive_fields = (
			"work_date",
			"selected_from",
			"selected_until",
			"assigned_role",
			"shift_location",
			"outside_availability_override",
		)
		changed = self.is_new() or not before or any(
			str(before.get(fieldname) or "") != str(self.get(fieldname) or "") for fieldname in sensitive_fields
		)
		confirmation_required = (
			application.commitment_type == "Ask me to confirm exact hours"
			or bool(self.outside_availability_override)
		)
		if changed and confirmation_required:
			self.employee_confirmation_status = "Pending"
			self.confirmation_requested_on = now_datetime()
			self.confirmed_on = None
		elif self.is_new() and not confirmation_required:
			self.employee_confirmation_status = "Not Required"

	def _validate_accounting_dimensions(self):
		if self.cost_center:
			company = frappe.db.get_value("Cost Center", self.cost_center, "company")
			if company and company != self.company:
				frappe.throw(_("Cost Center {0} does not belong to company {1}.").format(self.cost_center, self.company))
		if self.project:
			company = frappe.db.get_value("Project", self.project, "company")
			if company and company != self.company:
				frappe.throw(_("Project {0} does not belong to company {1}.").format(self.project, self.company))

	def _get_requirement(self, roster, start, end):
		requirement = None
		if self.coverage_requirement_idx:
			requirement = next(
				(row for row in roster.coverage_requirements if row.idx == int(self.coverage_requirement_idx)),
				None,
			)
			if not requirement:
				frappe.throw(_("Coverage requirement row {0} does not exist.").format(self.coverage_requirement_idx))
		else:
			for row in roster.coverage_requirements:
				row_start = combine_date_time(row.work_date, row.start_time)
				row_end = end_after_start(row_start, combine_date_time(row.work_date, row.end_time))
				role_matches = not self.assigned_role or self.assigned_role.strip().casefold() == (row.role or "").strip().casefold()
				if role_matches and row_start <= start and end <= row_end:
					requirement = row
					break
		if not requirement:
			frappe.throw(_("The selected hours do not fit any coverage requirement."))
		row_start = combine_date_time(requirement.work_date, requirement.start_time)
		row_end = end_after_start(row_start, combine_date_time(requirement.work_date, requirement.end_time))
		if not row_start <= start or not end <= row_end:
			frappe.throw(_("The selected hours must remain inside coverage row {0}.").format(requirement.idx))
		return requirement

	def _warn_if_requirement_is_fully_staffed(self, requirement, start, end):
		count = 0
		for other in frappe.get_all(
			"Roster Selection",
			filters={
				"roster": self.roster,
				"coverage_requirement_idx": requirement.idx,
				"docstatus": ["<", 2],
				"status": ["!=", "Declined"],
				"name": ["!=", self.name],
			},
			fields=["work_date", "selected_from", "selected_until"],
			limit_page_length=1000,
		):
			other_start = combine_date_time(other.work_date, other.selected_from)
			other_end = end_after_start(other_start, combine_date_time(other.work_date, other.selected_until))
			if start < other_end and other_start < end:
				count += 1
		if count >= int(requirement.required_headcount or 0):
			frappe.msgprint(
				_("Coverage row {0} is already fully staffed for part of this interval. The selection will still be saved.").format(requirement.idx),
				indicator="orange",
				alert=True,
			)

	def before_insert(self):
		self.selected_by = frappe.session.user
		self.selected_on = now_datetime()

	def after_insert(self):
		if frappe.db.get_value("Roster Application", self.application, "status") in {"Applied", "Standby"}:
			frappe.db.set_value("Roster Application", self.application, "status", "Selected", update_modified=False)
		if frappe.db.get_value("Casual Roster", self.roster, "status") in {"Open for Applications", "Applications Closed"}:
			frappe.db.set_value("Casual Roster", self.roster, "status", "Selecting", update_modified=False)
		if self.employee_confirmation_status == "Pending":
			frappe.publish_realtime(
				"malaysia_workforce:selection_confirmation",
				{"selection": self.name, "employee": self.employee},
				after_commit=True,
			)

	def on_trash(self):
		other = frappe.db.exists(
			"Roster Selection",
			{
				"application": self.application,
				"name": ["!=", self.name],
				"docstatus": ["<", 2],
				"status": ["!=", "Declined"],
			},
		)
		if not other:
			frappe.db.set_value("Roster Application", self.application, "status", "Applied", update_modified=False)

	def before_submit(self):
		if self.employee_confirmation_status == "Pending":
			frappe.throw(_("The employee must confirm the exact hours before this selection can be published."))
		if self.employee_confirmation_status == "Declined":
			frappe.throw(_("A declined selection cannot be published."))
		self.selected_by = self.selected_by or frappe.session.user
		self.selected_on = self.selected_on or now_datetime()

	def on_submit(self):
		from malaysia_workforce.roster.services import publish_selection

		publish_selection(self)
		self.db_set("status", "Published", update_modified=False)
		frappe.db.set_value("Roster Application", self.application, "status", "Selected", update_modified=False)

	def on_cancel(self):
		from malaysia_workforce.roster.services import cancel_selection

		cancel_selection(self)
		self.db_set("status", "Cancelled", update_modified=False)
