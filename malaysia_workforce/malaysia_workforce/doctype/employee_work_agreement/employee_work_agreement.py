from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today

from malaysia_workforce.utils import validate_date_range, validate_decimal


class EmployeeWorkAgreement(Document):
	def validate(self):
		validate_date_range(self.effective_from, self.effective_until, "work agreement")
		employee_company = frappe.db.get_value("Employee", self.employee, "company")
		if employee_company and self.company != employee_company:
			frappe.throw(_("Work Agreement company must match the Employee company."))
		numeric_fields = (
			"base_hourly_rate",
			"base_daily_rate",
			"per_shift_rate",
			"normal_daily_hours",
			"normal_weekly_hours",
			"comparable_full_time_daily_hours",
			"comparable_full_time_weekly_hours",
			"guaranteed_weekly_hours",
			"maximum_daily_hours",
			"maximum_weekly_hours",
			"minimum_shift_hours",
		)
		for fieldname in numeric_fields:
			validate_decimal(self.get(fieldname), self.meta.get_label(fieldname), minimum=0)
		if self.pay_basis == "Hourly" and validate_decimal(
			self.base_hourly_rate, _("Base Hourly Rate"), minimum="0.01", allow_blank=False
		) is None:
			frappe.throw(_("Base Hourly Rate is required for an hourly agreement."))
		if self.work_arrangement == "Part Time":
			for fieldname in (
				"normal_daily_hours",
				"normal_weekly_hours",
				"comparable_full_time_daily_hours",
				"comparable_full_time_weekly_hours",
			):
				if float(self.get(fieldname) or 0) <= 0:
					frappe.throw(_("{0} must be greater than zero for a part-time agreement.").format(self.meta.get_label(fieldname)))
			if float(self.normal_daily_hours) > float(self.comparable_full_time_daily_hours):
				frappe.throw(_("Normal Daily Hours cannot exceed Comparable Full-Time Daily Hours."))
			if float(self.normal_weekly_hours) > float(self.comparable_full_time_weekly_hours):
				frappe.throw(_("Normal Weekly Hours cannot exceed Comparable Full-Time Weekly Hours."))
		self._validate_minimum_wage()
		if (
			self.normal_weekly_hours
			and self.comparable_full_time_weekly_hours
			and self.normal_weekly_hours > self.comparable_full_time_weekly_hours
		):
			frappe.msgprint(
				_("Normal weekly hours exceed the comparable full-time hours. Review the work arrangement classification."),
				indicator="orange",
			)
		if self.maximum_daily_hours and self.normal_daily_hours and self.maximum_daily_hours < self.normal_daily_hours:
			frappe.throw(_("Maximum Daily Hours cannot be below Normal Daily Hours."))
		if self.maximum_weekly_hours and self.normal_weekly_hours and self.maximum_weekly_hours < self.normal_weekly_hours:
			frappe.throw(_("Maximum Weekly Hours cannot be below Normal Weekly Hours."))
		self._validate_overlap()

	def _validate_minimum_wage(self):
		if self.pay_basis != "Hourly" or not self.base_hourly_rate:
			return
		settings = frappe.get_cached_doc("Malaysia Workforce Settings")
		if not settings.minimum_wage_effective_from or not settings.minimum_hourly_rate:
			return
		agreement_end = getdate(self.effective_until or "2999-12-31")
		if agreement_end >= getdate(settings.minimum_wage_effective_from) and float(
			self.base_hourly_rate
		) < float(settings.minimum_hourly_rate):
			frappe.throw(
				_("Hourly rate RM {0:.2f} is below the configured minimum of RM {1:.2f} effective {2}.").format(
					float(self.base_hourly_rate),
					float(settings.minimum_hourly_rate),
					settings.minimum_wage_effective_from,
				)
			)

	def _validate_overlap(self):
		filters = {"employee": self.employee, "name": ["!=", self.name]}
		for other in frappe.get_all(
			"Employee Work Agreement",
			filters=filters,
			fields=["name", "effective_from", "effective_until"],
			limit_page_length=500,
		):
			other_end = getdate(other.effective_until or "2999-12-31")
			this_end = getdate(self.effective_until or "2999-12-31")
			if getdate(self.effective_from) <= other_end and getdate(other.effective_from) <= this_end:
				frappe.throw(_("Work Agreement {0} overlaps this effective period.").format(other.name))

	def on_update(self):
		today_date = getdate(today())
		if getdate(self.effective_from) <= today_date <= getdate(self.effective_until or "2999-12-31"):
			frappe.db.set_value(
				"Employee",
				self.employee,
				{
					"custom_employee_work_agreement": self.name,
					"custom_work_arrangement": self.work_arrangement,
					"custom_malaysia_legal_jurisdiction": self.jurisdiction,
				},
				update_modified=False,
			)
