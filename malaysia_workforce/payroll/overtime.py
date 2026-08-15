from __future__ import annotations

from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import get_first_day, get_last_day, getdate


def _month_key(value) -> tuple[int, int]:
	day = getdate(value)
	return day.year, day.month


def _add_monthly_hours(totals: dict[tuple[int, int], Decimal], rows) -> None:
	for row in rows:
		key = _month_key(row.date)
		hours = getattr(row, "overtime_duration", None)
		if hours is None:
			hours = getattr(row, "hours", 0)
		totals[key] = totals.get(key, Decimal("0")) + Decimal(str(hours or 0))


class MalaysiaOvertimeMixin:
	"""Narrow HRMS Overtime Slip extension for Malaysian ordinary-rate rules."""

	def validate(self):
		super().validate()
		if not self._malaysia_enabled():
			return
		monthly = {}
		_add_monthly_hours(monthly, self.overtime_details or [])
		existing_rows = frappe.db.sql(
			"""select detail.date, sum(detail.overtime_duration) as hours
			from `tabOvertime Details` detail
			inner join `tabOvertime Slip` slip on slip.name=detail.parent
			where slip.employee=%s and slip.docstatus<2 and slip.name!=%s
			and detail.date between %s and %s
			group by detail.date""",
			(
				self.employee,
				self.name or "",
				get_first_day(self.start_date),
				get_last_day(self.end_date),
			),
			as_dict=True,
		)
		_add_monthly_hours(monthly, existing_rows)
		for (year, month), hours in sorted(monthly.items()):
			if hours > Decimal("104"):
				frappe.throw(
					_("Overtime exceeds the 104-hour limit for {0}-{1:02d}.").format(year, month)
				)
		contract = self._malaysia_contract()
		if not contract.custom_overtime_eligible:
			frappe.throw(_("The Employee's active Contract does not permit statutory overtime."))

	def _malaysia_enabled(self) -> bool:
		company = self.company or frappe.db.get_value("Employee", self.employee, "company")
		return bool(company and frappe.db.get_value("Company", company, "custom_enable_malaysia_payroll"))

	def _malaysia_contract(self):
		rows = frappe.get_all(
			"Contract", filters={"party_type": "Employee", "party_name": self.employee, "status": "Active",
				"start_date": ["<=", self.end_date]},
			fields=["name", "end_date", "custom_malaysia_wage_basis", "custom_contract_wage_rate", "custom_normal_hours_per_day",
				"custom_normal_hours_per_week", "custom_malaysia_work_classification",
				"custom_comparable_full_time_hours_per_day", "custom_overtime_eligible"], order_by="start_date desc",
		)
		for row in rows:
			if not row.end_date or getdate(row.end_date) >= getdate(self.start_date):
				return row
		frappe.throw(_("No active ERPNext Contract covers this Overtime Slip."))

	def _bulk_load_overtime_types(self, names):
		rows = super()._bulk_load_overtime_types(names)
		for item in frappe.get_all("Overtime Type", filters={"name": ["in", list(names)]},
			fields=["name", "custom_malaysia_pay_type"]):
			if item.name in rows:
				rows[item.name]["custom_malaysia_pay_type"] = item.custom_malaysia_pay_type
		return rows

	def _get_applicable_hourly_rate(self, overtime_type, standard_working_hours=0):
		pay_type = (self.overtime_types.get(overtime_type) or {}).get("custom_malaysia_pay_type")
		if not self._malaysia_enabled() or not pay_type:
			return super()._get_applicable_hourly_rate(overtime_type, standard_working_hours)
		if not hasattr(self, "_cached_salary_slip"):
			from hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment import get_assigned_salary_structure
			salary_structure = get_assigned_salary_structure(self.employee, self.start_date)
			self._cached_salary_slip = self._make_salary_slip(salary_structure)
		components = {
			row.name for row in frappe.get_all("Salary Component", filters={"custom_include_in_ordinary_rate": 1}, fields=["name"])
		}
		ordinary = sum(Decimal(str(row.amount or 0)) for row in self._cached_salary_slip.earnings
			if row.salary_component in components and not row.get("additional_salary"))
		contract = self._malaysia_contract()
		hours = Decimal(str(contract.custom_normal_hours_per_day or standard_working_hours or 8))
		if contract.custom_malaysia_wage_basis == "Hourly":
			return float(Decimal(str(contract.custom_contract_wage_rate)))
		if contract.custom_malaysia_wage_basis == "Daily":
			return float(Decimal(str(contract.custom_contract_wage_rate)) / hours)
		if contract.custom_malaysia_wage_basis == "Monthly":
			return float(ordinary / Decimal("26") / hours)
		payment_days = Decimal(str(max(self._cached_salary_slip.payment_days or 0, 1)))
		return float(ordinary / payment_days / hours)

	def get_attendance_records(self):
		if not self._malaysia_enabled():
			return super().get_attendance_records()
		rows = frappe.get_all(
			"Attendance",
			fields=["name", "attendance_date", "overtime_type", "actual_overtime_duration", "working_hours", "standard_working_hours"],
			filters={"employee": self.employee, "docstatus": 1, "attendance_date": ["between", [self.start_date, self.end_date]],
				"status": "Present", "overtime_type": ["!=", ""]},
		)
		if not rows:
			frappe.throw(_("No submitted overtime Attendance records were found for this period."))
		return rows

	def create_overtime_details_row_for_attendance(self, records):
		if not self._malaysia_enabled():
			return super().create_overtime_details_row_for_attendance(records)
		pay_types = {row.name: row.custom_malaysia_pay_type for row in frappe.get_all(
			"Overtime Type", filters={"name": ["in", list({item.overtime_type for item in records})]},
			fields=["name", "custom_malaysia_pay_type"])}
		self.overtime_details = []
		for record in records:
			pay_type = pay_types.get(record.overtime_type)
			duration = record.working_hours if pay_type in {"Rest Day", "Public Holiday"} else record.actual_overtime_duration
			if duration and duration > 0:
				self.append("overtime_details", {"reference_document": record.name, "date": record.attendance_date,
					"overtime_type": record.overtime_type, "overtime_duration": duration,
					"standard_working_hours": record.standard_working_hours})

	def calculate_overtime_amount(self, overtime_type, hourly_rate, duration, overtime_date, holiday_date_map):
		pay_type = (self.overtime_types.get(overtime_type) or {}).get("custom_malaysia_pay_type")
		if not self._malaysia_enabled() or not pay_type:
			return super().calculate_overtime_amount(overtime_type, hourly_rate, duration, overtime_date, holiday_date_map)
		rate = Decimal(str(hourly_rate))
		hours = Decimal(str(duration))
		normal = Decimal(str(self._malaysia_contract().custom_normal_hours_per_day or 8))
		from malaysia_workforce.payroll.wages import (
			overtime_pay, part_time_additional_work_pay, part_time_public_holiday_work_pay,
			part_time_rest_day_work_pay, public_holiday_work_pay, rest_day_work_pay,
		)
		contract = self._malaysia_contract()
		if contract.custom_malaysia_work_classification == "Part-time":
			full_time = Decimal(str(contract.custom_comparable_full_time_hours_per_day))
			if pay_type == "Normal Overtime":
				return float(part_time_additional_work_pay(rate, hours, normal, full_time))
			if pay_type == "Public Holiday":
				return float(part_time_public_holiday_work_pay(rate, hours, normal, full_time))
			return float(part_time_rest_day_work_pay(rate, hours, normal, full_time))
		if pay_type == "Normal Overtime":
			return float(overtime_pay(rate, hours))
		if pay_type == "Public Holiday":
			return float(public_holiday_work_pay(rate, hours, normal))
		return float(rest_day_work_pay(rate, hours, normal, monthly_rated=contract.custom_malaysia_wage_basis == "Monthly"))
