import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from malaysia_workforce.forms.validation import (
	TP3_MONEY_FIELDS,
	date_overlaps_tax_year,
	nonnegative_decimal,
	validate_tax_year,
)
from malaysia_workforce.permissions import current_employee, is_tax_privileged
from malaysia_workforce.utils import stable_json

FINAL_STATUSES = {"Accepted by Employer", "Superseded"}


def _payload(doc) -> str:
	return stable_json(
		{
			"employee": doc.employee,
			"company": doc.company,
			"tax_year": int(doc.tax_year or 0),
			"previous_employer_name": doc.previous_employer_name,
			"previous_employer_number": doc.previous_employer_number,
			"employment_start": str(doc.employment_start or ""),
			"employment_end": str(doc.employment_end or ""),
			**{fieldname: str(doc.get(fieldname) or 0) for fieldname in TP3_MONEY_FIELDS},
			"employee_declaration": int(doc.employee_declaration or 0),
		}
	)


class MalaysiaPreviousEmploymentTP3(Document):
	def validate(self):
		privileged = is_tax_privileged()
		if not privileged:
			if self.employee != current_employee():
				frappe.throw(_("You can only maintain your own declaration."), frappe.PermissionError)
			if self.status not in {"Draft", "Submitted by Employee"}:
				frappe.throw(_("Only HR or Payroll may accept or supersede a declaration."), frappe.PermissionError)

		employee_company = frappe.db.get_value("Employee", self.employee, "company")
		if not employee_company:
			frappe.throw(_("Select a valid Employee."))
		if self.company != employee_company:
			frappe.throw(_("The declaration Company must match the Employee's Company."))
		try:
			self.tax_year = validate_tax_year(self.tax_year, getdate().year)
			for fieldname in TP3_MONEY_FIELDS:
				self.set(fieldname, nonnegative_decimal(self.get(fieldname), self.meta.get_label(fieldname)))
		except ValueError as exc:
			frappe.throw(_(str(exc)))

		if self.status != "Draft" and not self.employee_declaration:
			frappe.throw(_("The employee declaration must be accepted before submission."))
		if self.employment_start and self.employment_end and getdate(self.employment_end) < getdate(self.employment_start):
			frappe.throw(_("Previous employment end date cannot be before start date."))
		start = getdate(self.employment_start) if self.employment_start else None
		end = getdate(self.employment_end) if self.employment_end else None
		if not date_overlaps_tax_year(start, end, int(self.tax_year)):
			frappe.throw(_("Previous employment dates must overlap the selected Tax Year."))

		before = self.get_doc_before_save()
		if before and before.status in FINAL_STATUSES:
			if _payload(before) != _payload(self):
				frappe.throw(_("Accepted or superseded declaration data is immutable. Create a new declaration."))
			if before.status == "Accepted by Employer" and self.status not in FINAL_STATUSES:
				frappe.throw(_("An accepted declaration may only remain Accepted or be marked Superseded."))
			if before.status == "Superseded" and self.status != "Superseded":
				frappe.throw(_("A superseded declaration cannot be reopened."))

	def on_trash(self):
		if self.status != "Draft":
			frappe.throw(_("Only draft declarations may be deleted."), frappe.PermissionError)
