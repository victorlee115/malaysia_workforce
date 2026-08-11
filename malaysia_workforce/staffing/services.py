from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.utils import add_days, get_datetime, getdate, now_datetime

from malaysia_workforce.data_access import (
	get_malaysia_profile,
	get_statutory_profile,
	get_work_agreement,
)
from malaysia_workforce.staffing.intervals import assignment_intervals, coerce_time
from malaysia_workforce.staffing.allocator import (
	ALLOCATOR_VERSION,
	Demand,
	Interval,
	Worker,
	allocate_staff,
)
from malaysia_workforce.staffing.shift_types import get_or_create_managed_shift_type
from malaysia_workforce.utils import select_for_update, stable_json


def _combine(work_date, time_value) -> datetime:
	return datetime.combine(getdate(work_date), coerce_time(time_value))


def _requirements_payload(plan) -> list[dict]:
	return [
		{
			"key": row.requirement_key,
			"date": str(row.work_date),
			"start": str(row.start_time),
			"end": str(row.end_time),
			"headcount": int(row.required_headcount or 0),
			"designation": row.designation or "",
			"skill": row.required_skill or "",
			"criticality": row.criticality or "Normal",
			"override": int(row.is_date_override or 0),
			"override_reason": row.override_reason or "",
		}
		for row in plan.requirements
	]


def materialize_requirements(plan) -> None:
	template = frappe.get_doc("Cafe Coverage Template", plan.coverage_template)
	plan.set("requirements", [])
	plan.set("recommendations", [])
	day = getdate(plan.cycle_start)
	while day <= getdate(plan.cycle_end):
		weekday = day.strftime("%A")
		for source in template.coverage_rows:
			if source.weekday != weekday:
				continue
			payload = "|".join(
				(
					plan.planning_key,
					str(day),
					str(source.start_time),
					str(source.end_time),
					source.designation or "",
					source.required_skill or "",
					str(source.required_headcount or 0),
				)
			)
			plan.append(
				"requirements",
				{
					"requirement_key": hashlib.sha256(payload.encode()).hexdigest(),
					"work_date": day,
					"start_time": source.start_time,
					"end_time": source.end_time,
					"required_headcount": source.required_headcount,
					"designation": source.designation,
					"required_skill": source.required_skill,
					"criticality": source.criticality or "Normal",
				},
			)
		day = add_days(day, 1)
	if not plan.requirements:
		frappe.throw(_("The selected Coverage Template generated no requirements for this cycle."))
	plan.coverage_percent = 0
	plan.source_snapshot_hash = ""
	plan.warnings = "[]"


def _shift_assignment_intervals(plan) -> dict[str, tuple[Interval, ...]]:
	rows = frappe.get_all(
		"Shift Assignment",
		filters={
			"company": plan.company,
			"docstatus": 1,
			"start_date": ["<=", plan.cycle_end],
			"end_date": [">=", plan.cycle_start],
		},
		fields=["name", "employee", "shift_type", "start_date", "end_date"],
		limit=100000,
	)
	shift_names = sorted({row.shift_type for row in rows if row.shift_type})
	shift_times = {
		row.name: (row.start_time, row.end_time)
		for row in frappe.get_all(
			"Shift Type",
			filters={"name": ["in", shift_names]},
			fields=["name", "start_time", "end_time"],
			limit=100000,
		)
	}
	result: dict[str, list[Interval]] = defaultdict(list)
	for row in assignment_intervals(
		rows,
		shift_times=shift_times,
		range_start=getdate(plan.cycle_start),
		range_end=getdate(plan.cycle_end),
	):
		result[row["employee"]].append(Interval(row["start"], row["end"]))
	return {employee: tuple(values) for employee, values in result.items()}


def _leave_dates(plan) -> dict[str, set]:
	result: dict[str, set] = defaultdict(set)
	for row in frappe.get_all(
		"Leave Application",
		filters={
			"company": plan.company,
			"docstatus": 1,
			"status": "Approved",
			"from_date": ["<=", plan.cycle_end],
			"to_date": [">=", plan.cycle_start],
		},
		fields=["employee", "from_date", "to_date"],
		limit=100000,
	):
		day = max(getdate(row.from_date), getdate(plan.cycle_start))
		until = min(getdate(row.to_date), getdate(plan.cycle_end))
		while day <= until:
			result[row.employee].add(day)
			day = add_days(day, 1)
	return result


def _employee_skills(employee: str) -> frozenset[str]:
	return frozenset(
		frappe.db.sql(
			"""
			SELECT child.skill
			FROM `tabEmployee Skill` child
			INNER JOIN `tabEmployee Skill Map` skill_map ON skill_map.name=child.parent
			WHERE child.parenttype='Employee Skill Map' AND skill_map.employee=%s
			""",
			(employee,),
			pluck=True,
		)
	)


def _availability_doc(employee: str, plan):
	rows = frappe.get_all(
		"Casual Availability",
		filters={
			"employee": employee,
			"company": plan.company,
			"cycle_start": plan.cycle_start,
			"status": "Submitted",
			"manager_review_status": ["in", ["Not Required", "Approved"]],
		},
		fields=["name"],
		order_by="modified desc",
		limit=1,
	)
	name = rows[0].name if rows else None
	return frappe.get_doc("Casual Availability", name) if name else None


def _worker_inputs(plan) -> tuple[list[Worker], list[str], dict]:
	filters = {"company": plan.company, "status": "Active"}
	if plan.branch:
		filters["branch"] = plan.branch
	employees = frappe.get_all(
		"Employee",
		filters=filters,
		fields=[
			"name",
			"designation",
			"branch",
			"custom_staffing_priority",
			"custom_staffing_priority_effective_from",
			"custom_staffing_priority_expires_on",
		],
		order_by="name",
		limit=100000,
	)
	existing = _shift_assignment_intervals(plan)
	leaves = _leave_dates(plan)
	warnings = []
	workers = []
	eligible_count = 0
	submitted_count = 0
	for employee in employees:
		agreement = get_work_agreement(employee.name, plan.cycle_start)
		if not agreement or agreement.work_arrangement not in {"Casual", "Part Time"}:
			continue
		if agreement.effective_until and getdate(agreement.effective_until) < getdate(plan.cycle_end):
			warnings.append(f"{employee.name}: work agreement does not cover the full planning cycle.")
			continue
		if agreement.branch and plan.branch and agreement.branch != plan.branch:
			continue
		if agreement.shift_location and plan.shift_location and agreement.shift_location != plan.shift_location:
			continue
		eligible_count += 1
		if not get_malaysia_profile(employee.name) or not get_statutory_profile(employee.name, plan.cycle_start):
			warnings.append(f"{employee.name}: Malaysia payroll or statutory profile is incomplete.")
			continue
		availability = _availability_doc(employee.name, plan)
		if not availability:
			warnings.append(f"{employee.name}: no approved availability for this cycle.")
			continue
		submitted_count += 1
		windows = []
		for row in availability.availability_windows:
			if getdate(row.work_date) in leaves.get(employee.name, set()):
				continue
			if agreement.weekly_rest_day and getdate(row.work_date).strftime("%A") == agreement.weekly_rest_day:
				continue
			windows.append(Interval(_combine(row.work_date, row.available_from), _combine(row.work_date, row.available_until)))
		priority = employee.custom_staffing_priority or "Standard"
		if (
			not employee.custom_staffing_priority_effective_from
			or getdate(employee.custom_staffing_priority_effective_from) > getdate(plan.cycle_start)
			or not employee.custom_staffing_priority_expires_on
			or getdate(employee.custom_staffing_priority_expires_on) < getdate(plan.cycle_start)
		):
			priority = "Standard"
		existing_intervals = existing.get(employee.name, ())
		projected = sum(interval.minutes for interval in existing_intervals) / 60
		workers.append(
			Worker(
				employee=employee.name,
				availability=tuple(windows),
				designation=employee.designation or "",
				skills=_employee_skills(employee.name),
				priority=priority,
				projected_hours=projected,
				submitted_on=get_datetime(availability.submitted_on or availability.modified),
				maximum_daily_hours=float(agreement.maximum_daily_hours or 12),
				maximum_weekly_hours=float(agreement.maximum_weekly_hours or 45),
				minimum_shift_hours=float(agreement.minimum_shift_hours or 2),
				split_shifts_allowed=bool(agreement.split_shifts_allowed),
				existing_intervals=existing_intervals,
			)
		)
	return workers, warnings, {"eligible": eligible_count, "submitted": submitted_count}


def _worker_payload(worker: Worker) -> dict:
	return {
		"employee": worker.employee,
		"designation": worker.designation,
		"skills": sorted(worker.skills),
		"priority": worker.priority,
		"projected_hours": worker.projected_hours,
		"submitted_on": str(worker.submitted_on),
		"maximum_daily_hours": worker.maximum_daily_hours,
		"maximum_weekly_hours": worker.maximum_weekly_hours,
		"minimum_shift_hours": worker.minimum_shift_hours,
		"split_shifts_allowed": worker.split_shifts_allowed,
		"availability": [(item.start.isoformat(), item.end.isoformat()) for item in worker.availability],
		"existing": [(item.start.isoformat(), item.end.isoformat()) for item in worker.existing_intervals],
	}


def current_source(plan) -> tuple[str, list[Worker], list[str], dict]:
	workers, warnings, counts = _worker_inputs(plan)
	payload = {
		"allocator_version": ALLOCATOR_VERSION,
		"company": plan.company,
		"branch": plan.branch or "",
		"shift_location": plan.shift_location or "",
		"cycle_start": str(plan.cycle_start),
		"cycle_end": str(plan.cycle_end),
		"requirements": _requirements_payload(plan),
		"workers": [_worker_payload(worker) for worker in workers],
		"warnings": sorted(warnings),
	}
	return hashlib.sha256(stable_json(payload).encode()).hexdigest(), workers, warnings, counts


def _demands(plan) -> list[Demand]:
	return [
		Demand(
			key=row.requirement_key,
			work_date=getdate(row.work_date),
			start=_combine(row.work_date, row.start_time),
			end=_combine(row.work_date, row.end_time),
			headcount=int(row.required_headcount),
			designation=row.designation or "",
			required_skill=row.required_skill or "",
			critical=row.criticality == "Critical",
		)
		for row in plan.requirements
	]


def generate_proposal(plan) -> None:
	if not plan.requirements:
		frappe.throw(_("Open availability before generating the proposal."))
	source_hash, workers, warnings, counts = current_source(plan)
	settings = frappe.get_cached_doc("Malaysia Workforce Settings")
	result = allocate_staff(
		_demands(plan),
		workers,
		slot_minutes=int(settings.staffing_slot_minutes or 30),
		preferred_minimum_hours=float(settings.preferred_minimum_shift_hours or 4),
		normal_minimum_hours=float(settings.normal_minimum_shift_hours or 2),
		maximum_assignment_hours=float(settings.maximum_recommended_shift_hours or 8),
	)
	plan.set("recommendations", [])
	requirements = {row.requirement_key: row for row in plan.requirements}
	worker_map = {worker.employee: worker for worker in workers}
	for assignment in result.assignments:
		requirement = requirements[assignment.requirement_key]
		agreement = get_work_agreement(assignment.employee, assignment.start.date(), required=True)
		plan.append(
			"recommendations",
			{
				"recommendation_key": hashlib.sha256(
					f"{plan.name}|{assignment.key}".encode()
				).hexdigest(),
				"requirement_key": assignment.requirement_key,
				"employee": assignment.employee,
				"work_date": assignment.start.date(),
				"start_time": assignment.start.time(),
				"end_time": assignment.end.time(),
				"duration_hours": assignment.hours,
				"designation": requirement.designation,
				"staffing_priority": worker_map[assignment.employee].priority,
				"rate_snapshot": agreement.base_hourly_rate,
				"employee_confirmation_status": "Not Required",
			},
		)
	allocated = defaultdict(int)
	uncovered = defaultdict(int)
	critical_uncovered = 0
	for assignment in result.assignments:
		allocated[assignment.requirement_key] += 1
	for gap in result.gaps:
		minutes = int((gap.end - gap.start).total_seconds() // 60) * gap.missing_headcount
		uncovered[gap.requirement_key] += minutes
		if gap.critical:
			critical_uncovered += minutes
	for requirement in plan.requirements:
		requirement.allocated_headcount = allocated[requirement.requirement_key]
		requirement.uncovered_minutes = uncovered[requirement.requirement_key]
	gap_messages = [
		f"{gap.requirement_key[:8]}: {gap.start:%Y-%m-%d %H:%M}–{gap.end:%H:%M} remains uncovered."
		for gap in result.gaps
	]
	plan.allocator_version = ALLOCATOR_VERSION
	plan.source_snapshot_hash = source_hash
	plan.generated_on = now_datetime()
	plan.eligible_employee_count = counts["eligible"]
	plan.submitted_availability_count = counts["submitted"]
	plan.required_minutes = result.required_minutes
	plan.covered_minutes = result.covered_minutes
	plan.coverage_percent = result.coverage_percent
	plan.critical_uncovered_minutes = critical_uncovered
	plan.unresolved_exception_count = len(result.gaps)
	plan.warnings = json.dumps(sorted(warnings + gap_messages), indent=2)
	if result.gaps:
		from malaysia_workforce.compliance.exceptions import create_assigned_exception

		create_assigned_exception(
			code=f"STAFFING-GAPS-{plan.name}",
			description=f"Resolve {len(result.gaps)} coverage gap(s) in staffing plan {plan.name}.",
			reference_type="Cafe Staffing Plan",
			reference_name=plan.name,
			due_date=getdate(plan.approval_due),
			allocated_to=plan.manager,
		)


def assert_source_unchanged(plan) -> None:
	if not plan.source_snapshot_hash:
		frappe.throw(_("Generate a staffing proposal before approval."))
	current_hash, _, _, _ = current_source(plan)
	if current_hash != plan.source_snapshot_hash:
		frappe.throw(_("Availability, leave, employee eligibility, or existing shifts changed. Return the plan to Collecting Availability and regenerate."))


def recommendation_within_availability(plan, row) -> bool:
	availability = _availability_doc(row.employee, plan)
	if not availability:
		return False
	start = _combine(row.work_date, row.start_time)
	end = _combine(row.work_date, row.end_time)
	return any(
		_combine(window.work_date, window.available_from) <= start
		and _combine(window.work_date, window.available_until) >= end
		for window in availability.availability_windows
		if getdate(window.work_date) == getdate(row.work_date)
	)


def _all_published(plan) -> list[str] | None:
	if not plan.recommendations:
		return None
	assignments = []
	for row in plan.recommendations:
		name = row.shift_assignment or frappe.db.get_value(
			"Shift Assignment",
			{"custom_malaysia_staffing_recommendation_key": row.recommendation_key, "docstatus": ["<", 2]},
			"name",
		)
		if not name:
			return None
		assignments.append(name)
	return assignments


def publish_plan(plan) -> list[str]:
	select_for_update("SELECT name FROM `tabCafe Staffing Plan` WHERE name=%s", (plan.name,))
	existing = _all_published(plan)
	if existing:
		return existing
	assert_source_unchanged(plan)
	created = []
	assignment_meta = frappe.get_meta("Shift Assignment")
	for row in plan.recommendations:
		shift_type = get_or_create_managed_shift_type(row.start_time, row.end_time)
		assignment = frappe.new_doc("Shift Assignment")
		assignment.employee = row.employee
		assignment.company = plan.company
		assignment.shift_type = shift_type
		assignment.start_date = row.work_date
		assignment.end_date = row.work_date
		if assignment_meta.has_field("shift_location"):
			assignment.shift_location = plan.shift_location
		assignment.custom_malaysia_staffing_plan = plan.name
		assignment.custom_malaysia_staffing_recommendation_key = row.recommendation_key
		assignment.custom_malaysia_assigned_designation = row.designation
		assignment.custom_malaysia_rate_snapshot = row.rate_snapshot
		assignment.custom_malaysia_source_hash = plan.source_snapshot_hash
		assignment.insert(ignore_permissions=True)
		assignment.submit()
		created.append(assignment.name)
		frappe.db.set_value(
			"Cafe Staffing Recommendation",
			row.name,
			{"shift_type": shift_type, "shift_assignment": assignment.name},
			update_modified=False,
		)
	frappe.db.set_value(
		"Cafe Staffing Plan",
		plan.name,
		{"approved_by": frappe.session.user, "approved_on": now_datetime()},
		update_modified=True,
	)
	return created
