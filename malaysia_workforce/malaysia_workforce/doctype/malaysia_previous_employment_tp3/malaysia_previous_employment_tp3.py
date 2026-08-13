import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime

from malaysia_workforce.payroll.tax_validation import (
	TP3_MONEY_FIELDS,
	date_overlaps_tax_year,
	manual_review_codes,
	nonnegative_decimal,
	submitted_relief_rows,
	validate_tax_year,
	validate_tp1_rows,
)
from malaysia_workforce.permissions import current_employee, is_tax_privileged
from malaysia_workforce.utils import ensure_roles


class MalaysiaPreviousEmploymentTP3(Document):
	def before_validate(self):
		if not is_tax_privileged():
			employee = current_employee()
			if not employee:
				frappe.throw(_("Your User is not linked to an active Employee."), frappe.PermissionError)
			self.employee = employee
			self.company = frappe.db.get_value("Employee", employee, "company")

	def validate(self):
		if not is_tax_privileged() and self.employee != current_employee():
			frappe.throw(_("You can only maintain your own declaration."), frappe.PermissionError)

		employee_company = frappe.db.get_value("Employee", self.employee, "company")
		if not employee_company:
			frappe.throw(_("Select a valid Employee."))
		if self.company != employee_company:
			frappe.throw(_("The declaration Company must match the Employee's Company."))
		try:
			self.tax_year = validate_tax_year(self.tax_year, getdate().year)
			for fieldname in TP3_MONEY_FIELDS:
				self.set(fieldname, nonnegative_decimal(self.get(fieldname), self.meta.get_label(fieldname)))
			if self.optional_reliefs:
				raise ValueError("Move the legacy Prior TP1 Reliefs total into itemised Relief Claims.")
			current_rows = [row.as_dict() for row in self.relief_claims]
			cleaned = validate_tp1_rows(current_rows, tax_year=self.tax_year)
			current_employer_rows = submitted_relief_rows(
				"Malaysia Tax Declaration TP1",
				employee=self.employee,
				company=self.company,
				tax_year=self.tax_year,
			)
			other_previous_rows = submitted_relief_rows(
				"Malaysia Previous Employment TP3",
				employee=self.employee,
				company=self.company,
				tax_year=self.tax_year,
				exclude=self.name,
			)
			validate_tp1_rows(
				current_rows + current_employer_rows + other_previous_rows,
				tax_year=self.tax_year,
			)
		except ValueError as exc:
			frappe.throw(_(str(exc)))
		for source, values in zip(self.relief_claims, cleaned, strict=True):
			for fieldname, value in values.items():
				source.set(fieldname, value)
		self.total_reliefs = sum((row.amount for row in self.relief_claims), 0)

		if self.employment_start and self.employment_end and getdate(self.employment_end) < getdate(self.employment_start):
			frappe.throw(_("Previous employment end date cannot be before start date."))
		start = getdate(self.employment_start) if self.employment_start else None
		end = getdate(self.employment_end) if self.employment_end else None
		if not date_overlaps_tax_year(start, end, int(self.tax_year)):
			frappe.throw(_("Previous employment dates must overlap the selected Tax Year."))
		if self.get("workflow_state") == "Pending Review" and not self.employee_declaration:
			frappe.throw(_("Accept the employee declaration before sending this TP3 for review."))

	def before_submit(self):
		ensure_roles("HR Manager", "System Manager")
		if not self.employee_declaration:
			frappe.throw(_("The employee declaration must be accepted before approval."))
		if not self.evidence:
			frappe.throw(_("Attach the signed TP3 before approval."))
		if current_employee() == self.employee:
			frappe.throw(_("You cannot approve your own TP3 declaration."), frappe.PermissionError)
		manual_codes = manual_review_codes(
			[row.as_dict() for row in self.relief_claims], tax_year=int(self.tax_year)
		)
		if manual_codes and not (self.manual_review_notes or "").strip():
			frappe.throw(
				_("HR Manager eligibility/sub-limit review notes are required for TP3 relief codes: {0}.").format(
					", ".join(manual_codes)
				)
			)
		self.manual_review_approved_by = frappe.session.user
		self.manual_review_approved_on = now_datetime()
		duplicate_filters = {
			"employee": self.employee,
			"company": self.company,
			"tax_year": self.tax_year,
			"previous_employer_name": self.previous_employer_name,
			"employment_start": self.employment_start,
			"employment_end": self.employment_end,
			"docstatus": 1,
			"name": ["!=", self.name],
		}
		if self.previous_employer_number:
			duplicate_filters["previous_employer_number"] = self.previous_employer_number
		duplicate = frappe.db.get_value(
			"Malaysia Previous Employment TP3",
			duplicate_filters,
			"name",
		)
		if duplicate:
			frappe.throw(
				_("Approved TP3 {0} already covers this previous employer and employment period.").format(
					duplicate
				)
			)
