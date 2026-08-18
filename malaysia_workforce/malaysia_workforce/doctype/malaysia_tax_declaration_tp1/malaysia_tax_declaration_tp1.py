from decimal import Decimal

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime

from malaysia_workforce.payroll.tax_validation import (
	manual_review_codes,
	submitted_relief_rows,
	validate_tax_year,
	validate_tp1_rows,
)
from malaysia_workforce.payroll.validation import ensure_employee_tax_profile
from malaysia_workforce.permissions import current_employee, is_tax_privileged
from malaysia_workforce.utils import ensure_roles


class MalaysiaTaxDeclarationTP1(Document):
	def before_validate(self):
		if not is_tax_privileged():
			employee = current_employee()
			if not employee:
				frappe.throw(_("Your User is not linked to an active Employee."), frappe.PermissionError)
			self.employee = employee
			self.company = frappe.db.get_value("Employee", employee, "company")

	def validate(self):
		privileged = is_tax_privileged()
		if not privileged:
			if self.employee != current_employee():
				frappe.throw(_("You can only maintain your own declaration."), frappe.PermissionError)

		employee_company = frappe.db.get_value("Employee", self.employee, "company")
		if not employee_company:
			frappe.throw(_("Select a valid Employee."))
		if self.company != employee_company:
			frappe.throw(_("The declaration Company must match the Employee's Company."))
		ensure_employee_tax_profile(self.employee)
		try:
			self.tax_year = validate_tax_year(self.tax_year, getdate().year)
			current_rows = [row.as_dict() for row in self.relief_claims]
			cleaned = validate_tp1_rows(current_rows, tax_year=self.tax_year)
			prior_rows = submitted_relief_rows(
				"Malaysia Previous Employment TP3",
				employee=self.employee,
				company=self.company,
				tax_year=self.tax_year,
			)
			validate_tp1_rows(prior_rows + current_rows, tax_year=self.tax_year)
		except ValueError as exc:
			frappe.throw(_(str(exc)))

		for source, values in zip(self.relief_claims, cleaned, strict=True):
			for fieldname, value in values.items():
				source.set(fieldname, value)
		self.total_reliefs = sum((Decimal(str(row.amount or 0)) for row in self.relief_claims), Decimal("0"))
		if self.get("workflow_state") == "Pending Review" and not self.employee_declaration:
			frappe.throw(_("Accept the employee declaration before sending this TP1 for review."))

	def before_submit(self):
		ensure_roles("HR Manager", "System Manager")
		if not self.employee_declaration:
			frappe.throw(_("The employee declaration must be accepted before approval."))
		if current_employee() == self.employee:
			frappe.throw(_("You cannot approve your own TP1 declaration."), frappe.PermissionError)
		manual_codes = manual_review_codes(
			[row.as_dict() for row in self.relief_claims], tax_year=int(self.tax_year)
		)
		if manual_codes and not (self.manual_review_notes or "").strip():
			frappe.throw(
				_("HR Manager eligibility/sub-limit review notes are required for TP1 codes: {0}.").format(
					", ".join(manual_codes)
				)
			)
		self.manual_review_approved_by = frappe.session.user
		self.manual_review_approved_on = now_datetime()
		other = frappe.db.get_value(
			"Malaysia Tax Declaration TP1",
			{
				"employee": self.employee,
				"company": self.company,
				"tax_year": self.tax_year,
				"docstatus": 1,
				"name": ["!=", self.name],
			},
			"name",
		)
		if other:
			frappe.throw(_("Approved declaration {0} already exists. Cancel or amend it first.").format(other))


@frappe.whitelist()
def relief_catalog(tax_year: int) -> dict[str, str]:
	"""Return the reviewed labels used to make the native child table understandable."""
	try:
		from malaysia_workforce.payroll.tax_validation import load_tp1_relief_rules

		return {code: row["label"] for code, row in load_tp1_relief_rules(int(tax_year)).items()}
	except (TypeError, ValueError) as exc:
		frappe.throw(_(str(exc)))
