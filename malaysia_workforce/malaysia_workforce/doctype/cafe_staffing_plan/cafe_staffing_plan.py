from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, get_datetime, getdate, now_datetime

from malaysia_workforce.staffing.intervals import coerce_time
from malaysia_workforce.utils import ensure_private_file, stable_json


def _minutes(value) -> int:
	parsed = coerce_time(value)
	return parsed.hour * 60 + parsed.minute


def _recommendation_snapshot(rows) -> list[dict]:
	result = [
		{
			"key": row.recommendation_key or row.name,
			"requirement": row.requirement_key or "",
			"employee": row.employee or "",
			"date": str(row.work_date or ""),
			"from": str(row.start_time or ""),
			"until": str(row.end_time or ""),
			"designation": row.designation or "",
		}
		for row in rows
	]
	return sorted(result, key=lambda row: stable_json(row))


class CafeStaffingPlan(Document):
	def validate(self):
		self.cycle_start = getdate(self.cycle_start)
		self.cycle_end = add_days(self.cycle_start, 13)
		self.planning_key = hashlib.sha256(
			f"{self.company}|{self.branch or ''}|{self.shift_location or ''}|{self.cycle_start}".encode()
		).hexdigest()
		self._set_deadline_defaults()
		self._validate_scope()
		self._validate_unique_cycle()
		before = self.get_doc_before_save()
		previous_state = before.workflow_state if before else None
		if self.workflow_state == "Collecting Availability" and previous_state != self.workflow_state:
			from malaysia_workforce.staffing.services import materialize_requirements

			materialize_requirements(self)
		if self.workflow_state == "Proposed" and previous_state != self.workflow_state:
			from malaysia_workforce.staffing.services import generate_proposal

			generate_proposal(self)
		if self.workflow_state in {"Proposed", "Approved"}:
			self._ensure_recommendation_keys()
			self._record_manager_adjustment(before)
			self._protect_requirements(before)
			self._validate_recommendations()

	def _ensure_recommendation_keys(self):
		seen = set()
		for row in self.recommendations:
			if not row.recommendation_key:
				payload = "|".join(
					(
						self.name or self.planning_key,
						"MANUAL",
						row.requirement_key or "",
						row.employee or "",
						str(row.work_date or ""),
						str(row.start_time or ""),
						str(row.end_time or ""),
					)
				)
				row.recommendation_key = hashlib.sha256(payload.encode()).hexdigest()
			if row.recommendation_key in seen:
				frappe.throw(_("Recommendation keys must be unique."))
			seen.add(row.recommendation_key)

	def _record_manager_adjustment(self, before):
		if not before or before.workflow_state != "Proposed":
			self.manual_override_audit = self.manual_override_audit or "[]"
			return
		old_rows = _recommendation_snapshot(before.recommendations)
		new_rows = _recommendation_snapshot(self.recommendations)
		if old_rows == new_rows:
			self.manual_override_audit = before.manual_override_audit or "[]"
			return
		reason = (self.manager_adjustment_reason or "").strip()
		if not reason:
			frappe.throw(_("Explain the manager adjustment before saving the proposal."))
		if not set(frappe.get_roles()) & {"Outlet Manager", "HR Manager", "Malaysia HR Manager", "System Manager"}:
			frappe.throw(_("Only an authorised staffing manager may adjust a proposal."), frappe.PermissionError)
		evidence = self.manager_adjustment_evidence or ""
		if evidence:
			evidence = ensure_private_file(evidence, _("Staffing plan adjustment evidence"))
		try:
			audit = json.loads(before.manual_override_audit or "[]")
		except (TypeError, ValueError):
			frappe.throw(_("The protected staffing adjustment audit is invalid."))
		if not isinstance(audit, list):
			frappe.throw(_("The protected staffing adjustment audit is invalid."))
		changed_keys = {
			row["key"]
			for row in old_rows + new_rows
			if next((item for item in old_rows if item["key"] == row["key"]), None)
			!= next((item for item in new_rows if item["key"] == row["key"]), None)
		}
		for row in self.recommendations:
			if row.recommendation_key in changed_keys:
				row.manual_override = 1
				row.override_reason = reason
		record = {
			"actor": frappe.session.user,
			"at": str(now_datetime()),
			"reason": reason,
			"evidence": evidence,
			"original": old_rows,
			"new": new_rows,
			"previous_hash": audit[-1].get("content_hash", "") if audit else "",
		}
		record["content_hash"] = hashlib.sha256(stable_json(record).encode()).hexdigest()
		audit.append(record)
		self.manual_override_audit = json.dumps(audit, indent=2)
		self.manager_adjustment_reason = ""
		self.manager_adjustment_evidence = ""

	def _set_deadline_defaults(self):
		settings = frappe.get_cached_doc("Malaysia Workforce Settings")
		if not self.availability_opens:
			self.availability_opens = get_datetime(
				add_days(self.cycle_start, -int(settings.availability_lead_days or 21))
			)
		if not self.availability_closes:
			self.availability_closes = get_datetime(
				add_days(self.cycle_start, -int(settings.availability_close_days or 7))
			) + timedelta(hours=23, minutes=59)
		if not self.approval_due:
			self.approval_due = get_datetime(
				add_days(self.cycle_start, -int(settings.approval_lead_days or 3))
			) + timedelta(hours=23, minutes=59)
		if not get_datetime(self.availability_opens) < get_datetime(self.availability_closes) < get_datetime(self.cycle_start):
			frappe.throw(_("Availability must open, close, and then precede the cycle start."))
		if not get_datetime(self.availability_closes) <= get_datetime(self.approval_due) < get_datetime(self.cycle_start):
			frappe.throw(_("The publish deadline must be after availability closes and before the cycle starts."))

	def _validate_scope(self):
		template = frappe.db.get_value(
			"Cafe Coverage Template",
			self.coverage_template,
			["company", "branch", "shift_location", "enabled", "effective_from", "effective_until"],
			as_dict=True,
		)
		if not template or not template.enabled:
			frappe.throw(_("Select an enabled Cafe Coverage Template."))
		if template.company != self.company or (template.branch or "") != (self.branch or "") or (template.shift_location or "") != (self.shift_location or ""):
			frappe.throw(_("Coverage Template company and location must match the Staffing Plan."))
		if getdate(template.effective_from) > self.cycle_start or getdate(template.effective_until or "2999-12-31") < self.cycle_end:
			frappe.throw(_("Coverage Template must be effective for the complete planning cycle."))

	def _validate_unique_cycle(self):
		existing = frappe.db.get_value(
			"Cafe Staffing Plan",
			{"planning_key": self.planning_key, "name": ["!=", self.name], "workflow_state": ["!=", "Superseded"]},
			"name",
		)
		if existing:
			frappe.throw(_("An active Staffing Plan already exists for this location and cycle: {0}.").format(existing))

	def _protect_requirements(self, before):
		if not before or before.workflow_state not in {"Proposed", "Approved"}:
			return
		fields = ("requirement_key", "work_date", "start_time", "end_time", "required_headcount", "designation", "required_skill", "criticality", "is_date_override", "override_reason")
		old = [[str(row.get(field) or "") for field in fields] for row in before.requirements]
		new = [[str(row.get(field) or "") for field in fields] for row in self.requirements]
		if old != new:
			frappe.throw(_("Return the plan to Collecting Availability before changing coverage requirements."))

	def _validate_recommendations(self):
		from malaysia_workforce.data_access import get_work_agreement
		from malaysia_workforce.staffing.allocator import Interval
		from malaysia_workforce.staffing.services import current_source, recommendation_within_availability

		requirements = {row.requirement_key: row for row in self.requirements}
		_, workers, _, _ = current_source(self)
		worker_map = {worker.employee: worker for worker in workers}
		seen = set()
		planned = defaultdict(list)
		for row in self.recommendations:
			if row.requirement_key not in requirements:
				frappe.throw(_("Recommendation row {0} has no matching coverage requirement.").format(row.idx))
			requirement = requirements[row.requirement_key]
			worker = worker_map.get(row.employee)
			if not worker:
				frappe.throw(_("{0} is not eligible for this staffing plan.").format(row.employee))
			start = _minutes(row.start_time)
			end = _minutes(row.end_time)
			if start % 30 or end % 30 or end <= start:
				frappe.throw(_("Recommendation row {0} has invalid times.").format(row.idx))
			row.duration_hours = (end - start) / 60
			if row.duration_hours < 1:
				frappe.throw(_("Recommendation row {0} must be at least one hour.").format(row.idx))
			if getdate(row.work_date) != getdate(requirement.work_date):
				frappe.throw(_("Recommendation row {0} must use its coverage requirement date.").format(row.idx))
			if start < _minutes(requirement.start_time) or end > _minutes(requirement.end_time):
				frappe.throw(_("Recommendation row {0} must remain within its coverage period.").format(row.idx))
			if row.designation != requirement.designation or worker.designation != requirement.designation:
				frappe.throw(_("{0} does not have the required Designation.").format(row.employee))
			if requirement.required_skill and requirement.required_skill not in worker.skills:
				frappe.throw(_("{0} does not have the required Skill.").format(row.employee))
			agreement = get_work_agreement(row.employee, row.work_date, required=True)
			if row.duration_hours < float(agreement.minimum_shift_hours or 0):
				frappe.throw(_("Recommendation row {0} is below the employee's effective agreement minimum.").format(row.idx))
			if agreement.weekly_rest_day and getdate(row.work_date).strftime("%A") == agreement.weekly_rest_day:
				frappe.throw(_("{0} cannot be assigned on the effective agreement rest day.").format(row.employee))
			if frappe.db.exists(
				"Leave Application",
				{
					"employee": row.employee,
					"docstatus": 1,
					"status": "Approved",
					"from_date": ["<=", row.work_date],
					"to_date": [">=", row.work_date],
				},
			):
				frappe.throw(_("{0} is on approved leave on {1}.").format(row.employee, row.work_date))
			key = (row.employee, str(row.work_date), start, end)
			if key in seen:
				frappe.throw(_("Duplicate recommendation for {0} on {1}.").format(row.employee, row.work_date))
			seen.add(key)
			proposed = Interval(
				get_datetime(f"{row.work_date} {coerce_time(row.start_time)}"),
				get_datetime(f"{row.work_date} {coerce_time(row.end_time)}"),
			)
			if any(proposed.start < existing.end and existing.start < proposed.end for existing in worker.existing_intervals):
				frappe.throw(_("{0} already has an overlapping Shift Assignment.").format(row.employee))
			if any(proposed.start < existing.end and existing.start < proposed.end for existing in planned[row.employee]):
				frappe.throw(_("Recommendations for {0} overlap.").format(row.employee))
			if not agreement.split_shifts_allowed:
				for existing in list(worker.existing_intervals) + planned[row.employee]:
					if existing.start.date() == proposed.start.date() and proposed.start != existing.end and proposed.end != existing.start:
						frappe.throw(_("The effective agreement does not allow split shifts for {0}.").format(row.employee))
			planned[row.employee].append(proposed)
			inside = recommendation_within_availability(self, row)
			emergency = row.duration_hours < 2
			if not inside or emergency:
				if not row.manual_override or not (row.override_reason or "").strip():
					frappe.throw(_("Outside-availability and sub-two-hour assignments require a documented manual exception."))
				if row.employee_confirmation_status != "Accepted" or not row.employee_confirmation_evidence:
					frappe.throw(_("Attach explicit employee acceptance before publishing this exception."))
				row.employee_confirmation_evidence = ensure_private_file(
					row.employee_confirmation_evidence, _("Employee staffing exception confirmation")
				)
			else:
				row.employee_confirmation_status = "Not Required"
		for employee, intervals in planned.items():
			worker = worker_map[employee]
			combined = list(worker.existing_intervals) + intervals
			for work_date in {item.start.date() for item in intervals}:
				daily = sum(item.minutes for item in combined if item.start.date() == work_date) / 60
				if worker.maximum_daily_hours and daily > worker.maximum_daily_hours:
					frappe.throw(_("Recommendations exceed the daily-hour limit for {0}.").format(employee))
				week_start = work_date - timedelta(days=work_date.weekday())
				weekly = sum(
					item.minutes for item in combined
					if item.start.date() - timedelta(days=item.start.date().weekday()) == week_start
				) / 60
				if worker.maximum_weekly_hours and weekly > worker.maximum_weekly_hours:
					frappe.throw(_("Recommendations exceed the weekly-hour limit for {0}.").format(employee))

	def before_submit(self):
		if self.workflow_state != "Approved":
			frappe.throw(_("A Staffing Plan may only be submitted through the Approved workflow state."))
		from malaysia_workforce.staffing.services import assert_source_unchanged

		assert_source_unchanged(self)

	def on_submit(self):
		from malaysia_workforce.staffing.services import publish_plan

		publish_plan(self)

	def on_update(self):
		before = self.get_doc_before_save()
		if not before or (before.manual_override_audit or "[]") == (self.manual_override_audit or "[]"):
			return
		from malaysia_workforce.compliance.exceptions import create_assigned_exception

		latest = json.loads(self.manual_override_audit)[-1]
		create_assigned_exception(
			code=f"STAFFING-OVERRIDE-{self.name}-{latest['content_hash'][:12]}",
			description=f"Review the documented manager adjustment on staffing plan {self.name}.",
			reference_type=self.doctype,
			reference_name=self.name,
			due_date=getdate(self.approval_due),
			allocated_to=self.manager,
		)

	def before_cancel(self):
		if any(row.shift_assignment for row in self.recommendations):
			frappe.throw(_("Cancel affected Shift Assignments instead of cancelling a published Staffing Plan."))
