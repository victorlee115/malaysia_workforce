from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import getdate

from malaysia_workforce.data_access import get_work_agreement
from malaysia_workforce.roster.coverage import Assignment, Requirement, TimeWindow, coverage_grid, recommend_assignments
from malaysia_workforce.roster.shift_intervals import assignment_intervals
from malaysia_workforce.roster.skills import employee_has_required_skill
from malaysia_workforce.roster.shift_policy import DYNAMIC_SHIFT_POLICY, canonical_time, dynamic_shift_identity
from malaysia_workforce.utils import combine_date_time, end_after_start


def _verify_dynamic_shift_type(name: str, fingerprint: str, start_time, end_time) -> str:
	row = frappe.db.get_value(
		"Shift Type",
		name,
		[
			"start_time",
			"end_time",
			"enable_auto_attendance",
			"determine_check_in_and_check_out",
			"working_hours_calculation_based_on",
			"custom_dynamic_roster_shift",
			"custom_mw_configuration_fingerprint",
		],
		as_dict=True,
	)
	if not row:
		frappe.throw(_("Dynamic Shift Type {0} could not be created.").format(name))
	valid = (
		bool(row.custom_dynamic_roster_shift)
		and row.custom_mw_configuration_fingerprint == fingerprint
		and canonical_time(row.start_time) == canonical_time(start_time)
		and canonical_time(row.end_time) == canonical_time(end_time)
		and int(row.enable_auto_attendance or 0) == 0
		and row.determine_check_in_and_check_out == DYNAMIC_SHIFT_POLICY["determine_check_in_and_check_out"]
		and row.working_hours_calculation_based_on == DYNAMIC_SHIFT_POLICY["working_hours_calculation_based_on"]
	)
	if not valid:
		frappe.throw(
			_(
				"Shift Type {0} conflicts with the Malaysia Workforce managed shift policy. "
				"Do not reuse or manually alter managed dynamic shifts."
			).format(name)
		)
	return name


def get_or_create_dynamic_shift_type(start_time, end_time) -> str:
	name, fingerprint = dynamic_shift_identity(start_time, end_time)
	if frappe.db.exists("Shift Type", name):
		return _verify_dynamic_shift_type(name, fingerprint, start_time, end_time)
	doc = frappe.new_doc("Shift Type")
	doc.name = name
	doc.start_time = start_time
	doc.end_time = end_time
	for fieldname, value in DYNAMIC_SHIFT_POLICY.items():
		doc.set(fieldname, value)
	doc.custom_dynamic_roster_shift = 1
	doc.custom_mw_configuration_fingerprint = fingerprint
	doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
	return _verify_dynamic_shift_type(name, fingerprint, start_time, end_time)



def get_standard_shift_assignment_intervals(
	employees: str | list[str] | tuple[str, ...] | set[str],
	date_from,
	date_to,
) -> tuple[dict, ...]:
	"""Return submitted non-roster Shift Assignment intervals for conflict checks."""
	employee_list = [employees] if isinstance(employees, str) else sorted(set(employees))
	if not employee_list:
		return ()
	date_from = getdate(date_from)
	date_to = getdate(date_to)
	rows = frappe.get_all(
		"Shift Assignment",
		filters={
			"employee": ["in", employee_list],
			"docstatus": 1,
			"status": "Active",
			"start_date": ["<=", date_to],
		},
		fields=[
			"name",
			"employee",
			"shift_type",
			"start_date",
			"end_date",
			"custom_roster_selection",
			"custom_assigned_start_datetime",
			"custom_assigned_end_datetime",
		],
		limit_page_length=10000,
	)
	rows = [row for row in rows if getdate(row.end_date or row.start_date) >= date_from]
	shift_types = sorted({row.shift_type for row in rows if row.shift_type and not row.custom_roster_selection})
	shift_times = {}
	if shift_types:
		for row in frappe.get_all(
			"Shift Type",
			filters={"name": ["in", shift_types]},
			fields=["name", "start_time", "end_time"],
			limit_page_length=len(shift_types),
		):
			shift_times[row.name] = (row.start_time, row.end_time)
	try:
		return assignment_intervals(
			rows,
			shift_times=shift_times,
			range_start=date_from,
			range_end=date_to,
		)
	except ValueError as exc:
		frappe.throw(_(str(exc)))

def publish_selection(selection) -> dict:
	"""Create exactly one standard Shift Assignment for a submitted selection.

	The operation is intentionally idempotent so a retried submit hook cannot create a
	second assignment or a second payable work record.
	"""
	if selection.shift_assignment and frappe.db.exists("Shift Assignment", selection.shift_assignment):
		return {"shift_assignment": selection.shift_assignment, "shift_work_record": selection.shift_work_record}

	existing = frappe.db.get_value(
		"Shift Assignment", {"custom_roster_selection": selection.name, "docstatus": ["<", 2]}, "name"
	)
	if existing:
		selection.db_set("shift_assignment", existing, update_modified=False)
		work_record = frappe.db.get_value("Shift Work Record", {"shift_assignment": existing, "docstatus": ["<", 2]}, "name")
		if work_record:
			selection.db_set("shift_work_record", work_record, update_modified=False)
		return {"shift_assignment": existing, "shift_work_record": work_record}

	roster = frappe.get_doc("Casual Roster", selection.roster)
	shift_type = get_or_create_dynamic_shift_type(selection.selected_from, selection.selected_until)
	start = combine_date_time(selection.work_date, selection.selected_from)
	end = end_after_start(start, combine_date_time(selection.work_date, selection.selected_until))

	assignment = frappe.new_doc("Shift Assignment")
	assignment.employee = selection.employee
	assignment.company = selection.company
	assignment.shift_type = shift_type
	assignment.shift_location = selection.shift_location or roster.default_shift_location
	assignment.start_date = getdate(start)
	assignment.end_date = getdate(end)
	assignment.custom_casual_roster = selection.roster
	assignment.custom_roster_selection = selection.name
	assignment.custom_assigned_start_datetime = start
	assignment.custom_assigned_end_datetime = end
	assignment.custom_assigned_hourly_rate = selection.hourly_rate
	assignment.custom_assigned_role = selection.assigned_role
	assignment.insert(ignore_permissions=True)
	assignment.submit()

	selection.db_set("shift_assignment", assignment.name, update_modified=False)
	work_record = frappe.db.get_value("Shift Work Record", {"shift_assignment": assignment.name}, "name")
	if work_record:
		selection.db_set("shift_work_record", work_record, update_modified=False)
	return {"shift_assignment": assignment.name, "shift_work_record": work_record}


def cancel_selection(selection) -> None:
	work_record_name = selection.shift_work_record or frappe.db.get_value(
		"Shift Work Record", {"roster_selection": selection.name, "docstatus": ["<", 2]}, "name"
	)
	if work_record_name:
		work_record = frappe.get_doc("Shift Work Record", work_record_name)
		if work_record.status == "Payroll Generated" or work_record.additional_salary_references:
			frappe.throw(_("This selection has already generated payroll. Reverse the payroll batch first."))
		if work_record.docstatus == 1:
			work_record.cancel()
		elif work_record.docstatus == 0:
			work_record.status = "Cancelled"
			work_record.save(ignore_permissions=True)

	assignment_name = selection.shift_assignment or frappe.db.get_value(
		"Shift Assignment", {"custom_roster_selection": selection.name, "docstatus": ["<", 2]}, "name"
	)
	if assignment_name:
		assignment = frappe.get_doc("Shift Assignment", assignment_name)
		if assignment.docstatus == 1:
			assignment.cancel()
		elif assignment.docstatus == 0:
			frappe.delete_doc("Shift Assignment", assignment.name, ignore_permissions=True)


def build_coverage_grid(roster_name: str) -> list[dict]:
	roster = frappe.get_doc("Casual Roster", roster_name)
	requirements = []
	for row in roster.coverage_requirements:
		start = combine_date_time(row.work_date, row.start_time)
		end = end_after_start(start, combine_date_time(row.work_date, row.end_time))
		requirements.append(
			Requirement(
				start=start,
				end=end,
				headcount=int(row.required_headcount),
				role=row.role,
				key=str(row.idx),
			)
		)
	assignments = []
	for row in frappe.get_all(
		"Roster Selection",
		filters={"roster": roster_name, "docstatus": ["<", 2], "status": ["!=", "Declined"]},
		fields=["employee", "work_date", "selected_from", "selected_until", "assigned_role"],
	):
		start = combine_date_time(row.work_date, row.selected_from)
		end = end_after_start(start, combine_date_time(row.work_date, row.selected_until))
		assignments.append(Assignment(row.employee, start, end, row.assigned_role))
	slot_minutes = frappe.db.get_single_value("Malaysia Workforce Settings", "roster_slot_minutes") or 30
	return coverage_grid(requirements, assignments, slot_minutes=int(slot_minutes))


def recommend_for_requirement(roster_name: str, requirement_idx: int) -> list[dict]:
	roster = frappe.get_doc("Casual Roster", roster_name)
	if requirement_idx < 1 or requirement_idx > len(roster.coverage_requirements):
		frappe.throw(_("Invalid coverage requirement row."))
	row = roster.coverage_requirements[requirement_idx - 1]
	start = combine_date_time(row.work_date, row.start_time)
	end = end_after_start(start, combine_date_time(row.work_date, row.end_time))

	existing_selections = frappe.get_all(
		"Roster Selection",
		filters={"roster": roster_name, "docstatus": ["<", 2], "status": ["!=", "Declined"]},
		fields=["employee", "work_date", "selected_from", "selected_until", "assigned_role"],
		limit_page_length=5000,
	)
	assigned_for_requirement = 0
	allocated: dict[str, Decimal] = {}
	excluded: set[str] = set()
	for selection in existing_selections:
		selection_start = combine_date_time(selection.work_date, selection.selected_from)
		selection_end = end_after_start(
			selection_start, combine_date_time(selection.work_date, selection.selected_until)
		)
		allocated[selection.employee] = allocated.get(selection.employee, Decimal("0")) + Decimal(
			str((selection_end - selection_start).total_seconds() / 3600)
		)
		if (
			(selection.assigned_role or "").strip().casefold() == (row.role or "").strip().casefold()
			and selection_start < end
			and start < selection_end
		):
			assigned_for_requirement += 1

	remaining = max(int(row.required_headcount) - assigned_for_requirement, 0)
	if remaining == 0:
		return []
	requirement = Requirement(start, end, remaining, row.role, key=str(row.idx))

	# Any confirmed assignment at the same time is a hard exclusion, including shifts
	# from another roster. The final Roster Selection validation repeats this check.
	for selection in frappe.get_all(
		"Roster Selection",
		filters={"work_date": row.work_date, "docstatus": ["<", 2], "status": ["!=", "Declined"]},
		fields=["employee", "work_date", "selected_from", "selected_until"],
		limit_page_length=10000,
	):
		selection_start = combine_date_time(selection.work_date, selection.selected_from)
		selection_end = end_after_start(
			selection_start, combine_date_time(selection.work_date, selection.selected_until)
		)
		if selection_start < end and start < selection_end:
			excluded.add(selection.employee)

	applications = frappe.get_all(
		"Roster Application",
		filters={"roster": roster_name, "status": ["in", ["Applied", "Standby"]]},
		pluck="name",
		limit_page_length=5000,
	)
	application_docs = [frappe.get_doc("Roster Application", name) for name in applications]
	standard_intervals = get_standard_shift_assignment_intervals(
		[application.employee for application in application_docs], row.work_date, row.work_date
	)
	for interval in standard_intervals:
		if interval["start"] < end and start < interval["end"]:
			excluded.add(interval["employee"])

	candidate_windows: dict[str, tuple[TimeWindow, ...]] = {}
	max_hours: dict[str, Decimal] = {}
	requirement_hours = Decimal(str((end - start).total_seconds() / 3600))
	for application in application_docs:
		if application.employee in excluded:
			continue
		employee_status, roster_enabled = frappe.db.get_value(
			"Employee", application.employee, ["status", "custom_roster_enabled"]
		) or (None, None)
		if employee_status != "Active" or not roster_enabled:
			continue
		if not get_work_agreement(application.employee, row.work_date):
			continue
		if row.required_skill and not employee_has_required_skill(application.employee, row.required_skill):
			continue
		windows = []
		for availability in application.availability_windows:
			if getdate(availability.work_date) != getdate(row.work_date):
				continue
			minimum = Decimal(str(availability.minimum_assignment_hours or 0))
			maximum = Decimal(str(availability.maximum_assignment_hours or 0))
			if minimum and requirement_hours < minimum:
				continue
			if maximum and requirement_hours > maximum:
				continue
			window_start = combine_date_time(availability.work_date, availability.available_from)
			window_end = end_after_start(
				window_start, combine_date_time(availability.work_date, availability.available_until)
			)
			window_start -= timedelta(
				minutes=int(availability.can_start_earlier_minutes or 0)
			)
			window_end += timedelta(
				minutes=int(availability.can_finish_later_minutes or 0)
			)
			windows.append(TimeWindow(window_start, window_end, availability.preference))
		if windows:
			candidate_windows[application.employee] = tuple(windows)
			if application.maximum_hours:
				max_hours[application.employee] = Decimal(str(application.maximum_hours))

	recommended = recommend_assignments(
		requirement=requirement,
		candidate_windows=candidate_windows,
		already_assigned_hours=allocated,
		max_hours=max_hours,
		excluded_employees=excluded,
	)
	out = []
	for employee in recommended:
		agreement = get_work_agreement(employee, row.work_date)
		out.append(
			{
				"employee": employee,
				"employee_name": frappe.db.get_value("Employee", employee, "employee_name"),
				"coverage_requirement_idx": row.idx,
				"work_date": row.work_date,
				"assigned_role": row.role,
				"selected_from": row.start_time,
				"selected_until": row.end_time,
				"hourly_rate": row.hourly_rate or (agreement and agreement.get("base_hourly_rate")) or 0,
				"shift_location": row.shift_location or roster.default_shift_location,
				"cost_center": row.cost_center,
				"project": row.project or roster.project,
				"reasons": [
					"Available for the complete period",
					"No active overlapping roster or standard shift",
					"Within the application's stated maximum hours",
					"Ranked by fewer allocated hours, then preferred availability",
				],
			}
		)
	return out
