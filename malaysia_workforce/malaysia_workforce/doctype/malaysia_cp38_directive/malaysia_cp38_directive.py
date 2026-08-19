from decimal import Decimal

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from malaysia_workforce.payroll.validation import ensure_employee_tax_profile


def _compute_cp38_amounts(employee: str, effective_from, directive_amount) -> tuple[Decimal, Decimal]:
	deducted = frappe.db.sql(
		"""select coalesce(sum(sd.amount), 0)
		from `tabSalary Detail` sd
		inner join `tabSalary Slip` ss on ss.name=sd.parent
		where ss.employee=%s and ss.docstatus=1 and sd.parentfield='deductions'
		and sd.salary_component='CP38' and ss.end_date >= %s""",
		(employee, effective_from),
	)[0][0]
	deducted = Decimal(str(deducted))
	balance = max(Decimal(str(directive_amount)) - deducted, Decimal("0"))
	return deducted, balance


def _overlapping_directive(employee: str, effective_from, effective_to, exclude: str) -> str | None:
	"""Find a submitted CP38 Directive for this employee whose active period overlaps."""
	rows = frappe.db.sql(
		"""select name from `tabMalaysia CP38 Directive`
		where employee=%(employee)s and docstatus=1 and name!=%(exclude)s
		and effective_from <= %(to_bound)s
		and (effective_to is null or effective_to >= %(effective_from)s)""",
		{
			"employee": employee,
			"exclude": exclude or "",
			"effective_from": effective_from,
			"to_bound": effective_to or "9999-12-31",
		},
	)
	return rows[0][0] if rows else None


def refresh_cp38_balance(directive_name: str) -> None:
	"""Re-sync amount_deducted/balance after a Salary Slip CP38 deduction submits.

	`validate()` is the only place these normally recompute, so they go stale the moment a
	Salary Slip deducts CP38 without the Directive being re-saved. Uses `frappe.db.set_value`
	rather than a full `.save()` so it does not re-run `validate()`'s unrelated checks on an
	already-submitted Directive.
	"""
	directive = frappe.db.get_value(
		"Malaysia CP38 Directive", directive_name, ["employee", "effective_from", "directive_amount"], as_dict=True
	)
	if not directive:
		return
	deducted, balance = _compute_cp38_amounts(directive.employee, directive.effective_from, directive.directive_amount)
	frappe.db.set_value("Malaysia CP38 Directive", directive_name, {"amount_deducted": deducted, "balance": balance})


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
		overlapping = _overlapping_directive(self.employee, self.effective_from, self.effective_to, self.name)
		if overlapping:
			frappe.throw(_("Directive {0} already covers an overlapping period for this employee.").format(overlapping))
		self.amount_deducted, self.balance = _compute_cp38_amounts(self.employee, self.effective_from, self.directive_amount)

	def before_submit(self):
		if not self.evidence:
			frappe.throw(_("Attach the LHDN directive before submitting CP38."))
