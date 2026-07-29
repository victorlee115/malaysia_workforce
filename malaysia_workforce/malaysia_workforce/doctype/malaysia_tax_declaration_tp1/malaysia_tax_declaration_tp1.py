from decimal import Decimal

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from malaysia_workforce.forms.validation import validate_tax_year, validate_tp1_rows
from malaysia_workforce.permissions import current_employee, is_tax_privileged
from malaysia_workforce.utils import stable_json

FINAL_STATUSES = {"Accepted by Employer", "Superseded"}


def _payload(doc) -> str:
	return stable_json(
		{
			"employee": doc.employee,
			"company": doc.company,
			"tax_year": int(doc.tax_year or 0),
			"declaration_date": str(doc.declaration_date or ""),
			"employee_declaration": int(doc.employee_declaration or 0),
			"relief_claims": [
				{
					"relief_code": row.relief_code,
					"description": row.description,
					"amount": str(row.amount or 0),
					"claim_month": int(row.claim_month) if row.claim_month else None,
					"evidence_reference": row.evidence_reference,
					"notes": row.notes,
				}
				for row in doc.relief_claims
			],
		}
	)


class MalaysiaTaxDeclarationTP1(Document):
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
			cleaned = validate_tp1_rows([row.as_dict() for row in self.relief_claims])
		except ValueError as exc:
			frappe.throw(_(str(exc)))

		for source, values in zip(self.relief_claims, cleaned, strict=True):
			for fieldname, value in values.items():
				source.set(fieldname, value)
		self.total_reliefs = sum((Decimal(str(row.amount or 0)) for row in self.relief_claims), Decimal("0"))
		if self.status != "Draft" and not self.employee_declaration:
			frappe.throw(_("The employee declaration must be accepted before submission."))

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
