from __future__ import annotations

import frappe
from decimal import Decimal
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today

from malaysia_workforce.utils import validate_date_range, validate_decimal
from malaysia_workforce.compliance.scope import validate_work_agreement_scope


class EmployeeWorkAgreement(Document):
	def validate(self):
		validate_work_agreement_scope(self)
		validate_date_range(self.effective_from, self.effective_until, "work agreement")
		self._protect_relied_terms()
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
		if self.work_arrangement in {"Part Time", "Casual"} and self.pay_basis != "Hourly":
			frappe.throw(
				_("This release supports cafe roster pay for part-time and casual employees on an Hourly basis only. Use standard Frappe HR for other reviewed remuneration arrangements.")
			)
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

	def _protect_relied_terms(self):
		before = self.get_doc_before_save()
		if not before:
			return
		protected = (
			"employee",
			"company",
			"effective_from",
			"effective_until",
			"work_arrangement",
			"contract_relationship",
			"regularity",
			"jurisdiction",
			"pay_basis",
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
			"weekly_rest_day",
			"split_shifts_allowed",
			"branch",
			"shift_location",
		)
		changed = {
			fieldname
			for fieldname in protected
			if str(before.get(fieldname) or "") != str(self.get(fieldname) or "")
		}
		if not changed:
			return
		if changed == {"effective_until"} and self.effective_until:
			latest = frappe.get_all(
				"Salary Slip",
				filters={
					"employee": self.employee,
					"docstatus": 1,
					"end_date": [">=", self.effective_from],
					"custom_malaysia_statutory_snapshot": ["is", "set"],
				},
				fields=["end_date"],
				order_by="end_date desc",
				limit=1,
			)
			if not latest or getdate(self.effective_until) >= getdate(latest[0].end_date):
				return
		if frappe.db.exists(
			"Salary Slip",
			{
				"employee": self.employee,
				"docstatus": 1,
				"start_date": ["<=", self.effective_until or "2999-12-31"],
				"end_date": [">=", self.effective_from],
				"custom_malaysia_statutory_snapshot": ["is", "set"],
			},
		):
			frappe.throw(
				_("This legal-terms addendum has been relied upon by payroll. Create a new effective-dated agreement instead of editing it.")
			)

	def _validate_minimum_wage(self):
		if self.pay_basis != "Hourly" or not self.base_hourly_rate:
			return
		from malaysia_workforce.payroll.rules import minimum_hourly_wage

		try:
			minimum = minimum_hourly_wage(getdate(self.effective_from))
		except ValueError as exc:
			frappe.throw(_(str(exc)))
		if float(self.base_hourly_rate) < float(minimum):
			frappe.throw(
				_("Hourly rate RM {0:.2f} is below the reviewed minimum of RM {1:.2f} effective for {2}.").format(
					float(self.base_hourly_rate),
					float(minimum),
					self.effective_from,
				)
			)
		if self.work_arrangement in {"Part Time", "Casual", "Full Time"}:
			from malaysia_workforce.payroll.rules import validate_flexible_worker_classification

			try:
				validate_flexible_worker_classification(
					work_arrangement=self.work_arrangement,
					pay_basis=self.pay_basis,
					regularity=self.regularity,
					normal_weekly_hours=Decimal(str(self.normal_weekly_hours or 0)),
					comparable_full_time_weekly_hours=Decimal(
						str(self.comparable_full_time_weekly_hours or 0)
					),
				)
			except ValueError as exc:
				if self.work_arrangement == "Full Time":
					return
				frappe.throw(_(str(exc)))

	def _validate_overlap(self):
		filters = {"employee": self.employee, "name": ["!=", self.name]}
		for other in frappe.get_all(
			"Employee Work Agreement",
			filters=filters,
			fields=["name", "effective_from", "effective_until"],
			limit=500,
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
				{"custom_employee_work_agreement": self.name},
				update_modified=False,
			)

	def on_trash(self):
		if frappe.db.exists(
			"Salary Slip",
			{
				"employee": self.employee,
				"docstatus": 1,
				"start_date": ["<=", self.effective_until or "2999-12-31"],
				"end_date": [">=", self.effective_from],
				"custom_malaysia_statutory_snapshot": ["is", "set"],
			},
		):
			frappe.throw(_("A legal-terms addendum relied upon by payroll cannot be deleted."))
		linked = frappe.db.get_value("Employee", self.employee, "custom_employee_work_agreement")
		if linked == self.name:
			frappe.throw(_("The active legal-terms addendum cannot be deleted. End-date it and create a replacement."))
