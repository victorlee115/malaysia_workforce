from decimal import Decimal

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from malaysia_workforce.payroll.validation import ensure_employee_tax_profile


class MalaysiaCP38Directive(Document):
	def validate(self):
		employee_company = frappe.db.get_value("Employee", self.employee, "company")
		if not employee_company:
			frappe.throw(_("Select a valid Employee."))
		if employee_company != self.company:
			frappe.throw(_("Company must match the Employee's Company."))
		ensure_employee_tax_profile(self.employee)
		if self.effective_to and getdate(self.effective_to) < getdate(self.effective_from):
			frappe.throw(_("Effective To cannot be before Effective From."))
		if Decimal(str(self.directive_amount or 0)) <= 0:
			frappe.throw(_("Directive Amount must be greater than zero."))
		if Decimal(str(self.monthly_deduction or 0)) <= 0:
			frappe.throw(_("Monthly Deduction must be greater than zero."))
		deducted = frappe.db.sql(
			"""select coalesce(sum(sd.amount), 0)
			from `tabSalary Detail` sd
			inner join `tabSalary Slip` ss on ss.name=sd.parent
			where ss.employee=%s and ss.docstatus=1 and sd.parentfield='deductions'
			and sd.salary_component='CP38' and ss.end_date >= %s""",
			(self.employee, self.effective_from),
		)[0][0]
		self.amount_deducted = deducted
		self.balance = max(Decimal(str(self.directive_amount)) - Decimal(str(deducted)), Decimal("0"))

	def before_submit(self):
		if not self.evidence:
			frappe.throw(_("Attach the LHDN directive before submitting CP38."))
