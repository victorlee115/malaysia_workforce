from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime

from malaysia_workforce.data_access import get_work_agreement
from malaysia_workforce.payroll.pay_engine import ShiftPayInput, calculate_shift_pay, select_pay_interval
from malaysia_workforce.utils import validate_decimal


class ShiftWorkRecord(Document):
	def validate(self):
		if self.scheduled_end and self.scheduled_start and get_datetime(self.scheduled_end) <= get_datetime(self.scheduled_start):
			frappe.throw(_("Scheduled End must be after Scheduled Start."))
		paid_break = validate_decimal(self.paid_break_minutes, _("Paid Break Minutes"), minimum=0, allow_blank=False)
		unpaid_break = validate_decimal(self.unpaid_break_minutes, _("Unpaid Break Minutes"), minimum=0, allow_blank=False)
		if paid_break != int(paid_break) or unpaid_break != int(unpaid_break):
			frappe.throw(_("Break minutes must be whole numbers."))
		validate_decimal(self.rate_snapshot, _("Hourly Rate Snapshot"), minimum="0.01", allow_blank=False)
		self._validate_sources()
		if self.actual_check_in and self.actual_check_out:
			start, end = get_datetime(self.actual_check_in), get_datetime(self.actual_check_out)
			if end <= start:
				frappe.throw(_("Actual Check Out must be after Actual Check In."))
			worked_minutes = (end - start).total_seconds() / 60
			if worked_minutes > 24 * 60:
				frappe.throw(_("A shift work record cannot exceed 24 hours."))
			if int(self.unpaid_break_minutes or 0) + int(self.paid_break_minutes or 0) > worked_minutes:
				frappe.throw(_("Paid and unpaid break minutes cannot exceed the recorded shift duration."))
			self._calculate_pay()

	def _validate_sources(self):
		if not self.shift_assignment:
			return
		assignment = frappe.db.get_value(
			"Shift Assignment",
			self.shift_assignment,
			["employee", "company", "custom_malaysia_staffing_plan", "custom_malaysia_staffing_recommendation_key"],
			as_dict=True,
		)
		if not assignment:
			frappe.throw(_("Linked Shift Assignment does not exist."))
		if assignment.employee != self.employee or assignment.company != self.company:
			frappe.throw(_("Shift Work Record does not match its Shift Assignment."))
		if not assignment.custom_malaysia_staffing_plan or not assignment.custom_malaysia_staffing_recommendation_key:
			frappe.throw(_("Shift Work Records are created only from an approved Cafe Staffing Plan."))
		if self.staffing_plan != assignment.custom_malaysia_staffing_plan:
			frappe.throw(_("Staffing Plan does not match the Shift Assignment."))
		if self.staffing_recommendation_key != assignment.custom_malaysia_staffing_recommendation_key:
			frappe.throw(_("Staffing recommendation does not match the Shift Assignment."))

	def _calculate_pay(self):
		agreement = get_work_agreement(self.employee, self.work_date, required=True)
		settings = frappe.get_cached_doc("Malaysia Workforce Settings")
		actual_start = get_datetime(self.actual_check_in)
		actual_end = get_datetime(self.actual_check_out)
		scheduled_start = get_datetime(self.scheduled_start)
		scheduled_end = get_datetime(self.scheduled_end)
		effective_start, effective_end, interval_policy = select_pay_interval(
			actual_start=actual_start,
			actual_end=actual_end,
			scheduled_start=scheduled_start,
			scheduled_end=scheduled_end,
			status=self.status,
			auto_verified_policy=settings.auto_verified_pay_basis or "Capped Actual Time",
		)
		result = calculate_shift_pay(
			ShiftPayInput(
				actual_start=effective_start,
				actual_end=effective_end,
				hourly_rate=self.rate_snapshot,
				unpaid_break_minutes=self.unpaid_break_minutes or 0,
				paid_break_minutes=self.paid_break_minutes or 0,
				normal_part_time_daily_hours=agreement.get("normal_daily_hours") or 0,
				comparable_full_time_daily_hours=agreement.get("comparable_full_time_daily_hours") or 0,
				work_arrangement=agreement.get("work_arrangement") or "",
				pay_basis=agreement.get("pay_basis") or "",
				regularity=agreement.get("regularity") or "",
				normal_weekly_hours=agreement.get("normal_weekly_hours") or 0,
				comparable_full_time_weekly_hours=agreement.get("comparable_full_time_weekly_hours") or 0,
				is_rest_day=bool(self.is_rest_day),
				is_public_holiday=bool(self.is_public_holiday),
			)
		)
		self.approved_payable_hours = result.payable_hours
		self.ordinary_hours = result.ordinary_hours
		self.additional_hours = result.additional_hours
		self.overtime_hours = result.overtime_hours
		self.rest_day_hours = result.payable_hours if self.is_rest_day else 0
		self.public_holiday_hours = result.payable_hours if self.is_public_holiday else 0
		self.gross_pay = result.gross_pay
		self.set("pay_breakdown", [])
		for line in result.lines:
			line_values = line.to_dict()
			line_values["salary_component"] = line_values.pop("component")
			self.append("pay_breakdown", line_values)
		snapshot = result.to_dict()
		snapshot.update(
			{
				"actual_start": actual_start.isoformat(),
				"actual_end": actual_end.isoformat(),
				"scheduled_start": scheduled_start.isoformat(),
				"scheduled_end": scheduled_end.isoformat(),
				"effective_pay_start": effective_start.isoformat(),
				"effective_pay_end": effective_end.isoformat(),
				"attendance_pay_interval_policy": interval_policy,
				"agreement_pay_basis": agreement.get("pay_basis"),
				"work_arrangement": agreement.get("work_arrangement"),
				"rule_profile": (
					"PART_TIME_REGULATIONS_2010"
					if agreement.get("work_arrangement") == "Part Time"
					else "CASUAL_CONTRACT_RATE"
				),
			}
		)
		self.calculation_snapshot = json.dumps(snapshot, sort_keys=True)

	def before_submit(self):
		if self.status not in {"Approved", "Automatically Verified"}:
			frappe.throw(_("Only approved or automatically verified work records can be submitted."))
		if not self.actual_check_in or not self.actual_check_out:
			frappe.throw(_("Actual Check In and Actual Check Out are required before submission."))
		attendance = frappe.db.get_value(
			"Attendance",
			{
				"employee": self.employee,
				"attendance_date": self.work_date,
				"docstatus": 1,
				"status": ["in", ["Present", "Half Day"]],
			},
			"name",
		)
		if not attendance:
			frappe.throw(_("Submit the standard Attendance record before approving this payroll breakdown."))
		self.attendance = attendance
		self.approved_by = self.approved_by or frappe.session.user
		self.approved_on = self.approved_on or now_datetime()

	def before_cancel(self):
		if self.status == "Payroll Generated" or self.additional_salary_references:
			frappe.throw(_("Reverse the linked payroll records before cancelling this work record."))

	def on_cancel(self):
		self.db_set("status", "Cancelled", update_modified=False)

	def on_trash(self):
		if self.shift_assignment:
			frappe.throw(_("A derived Shift Work Record cannot be deleted; cancel it with retained audit history."))
