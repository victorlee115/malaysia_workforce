from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.model.document import Document

from malaysia_workforce.utils import validate_decimal


class MalaysiaEmployeeProfile(Document):
	def validate(self):
		employee_company = frappe.db.get_value("Employee", self.employee, "company")
		if employee_company and self.company != employee_company:
			frappe.throw(_("Malaysia Employee Profile company must match the Employee company."))

		self.nric_number = re.sub(r"[^0-9]", "", self.nric_number or "") or None
		self.old_ic_number = (self.old_ic_number or "").strip().upper() or None
		self.passport_number = re.sub(r"\s+", "", (self.passport_number or "").upper()) or None
		self.passport_country_code = (self.passport_country_code or "").strip().upper() or None
		if not (self.nric_number or self.passport_number):
			frappe.throw(_("Enter either an NRIC number or passport number."))
		if self.nric_number and (len(self.nric_number) != 12 or not self.nric_number.isdigit()):
			frappe.throw(_("NRIC Number must contain exactly 12 digits."))
		if self.nationality_status in {"Malaysian", "Permanent Resident"} and not self.nric_number:
			frappe.throw(_("NRIC Number is required for a Malaysian or Permanent Resident profile."))
		if self.nationality_status == "Non-Malaysian" and not self.passport_number:
			frappe.throw(_("Passport Number is required for a non-Malaysian employee."))
		if self.passport_number and self.nationality_status == "Non-Malaysian" and not self.passport_country_code:
			frappe.throw(_("Passport Country Code is required for a non-Malaysian employee."))
		if self.passport_country_code and not re.fullmatch(r"[A-Z]{2}", self.passport_country_code):
			frappe.throw(_("Passport Country Code must be a two-letter code."))
		self._validate_unique_identity("nric_number", self.nric_number, _("NRIC Number"))
		self._validate_unique_identity("passport_number", self.passport_number, _("Passport Number"))

		if int(self.tax_category or 0) not in {1, 2, 3}:
			frappe.throw(_("PCB Category must be 1, 2 or 3."))
		validate_decimal(self.child_units, _("Qualifying Child Units"), minimum=0, allow_blank=False)
		for fieldname in ("employee_extra_epf_rate", "employer_extra_epf_rate"):
			validate_decimal(
				self.get(fieldname),
				self.meta.get_label(fieldname),
				minimum=0,
				maximum=100,
				allow_blank=False,
			)

	def _validate_unique_identity(self, fieldname: str, value: str | None, label: str):
		if not value:
			return
		other = frappe.db.get_value(
			"Malaysia Employee Profile",
			{fieldname: value, "name": ["!=", self.name]},
			"employee",
		)
		if other:
			frappe.throw(_("{0} is already used by employee {1}.").format(label, other))

	def on_update(self):
		frappe.db.set_value(
			"Employee", self.employee, "custom_malaysia_employee_profile", self.name, update_modified=False
		)
		frappe.db.set_value(
			"Employee",
			self.employee,
			"custom_other_employment_declared",
			self.other_employment_declared,
			update_modified=False,
		)
