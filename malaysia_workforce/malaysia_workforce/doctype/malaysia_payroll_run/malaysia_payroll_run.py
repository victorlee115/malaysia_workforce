from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from malaysia_workforce.utils import validate_date_range


class MalaysiaPayrollRun(Document):
	def validate(self):
		if self.payroll_frequency == "Monthly":
			self.is_final_run_for_month = 1
		validate_date_range(self.start_date, self.end_date, "payroll run")
		if getdate(self.payroll_date) < getdate(self.start_date):
			frappe.throw(_("Payroll Date cannot be before the payroll period starts."))
		self._lock_frozen_source_fields()

	def _lock_frozen_source_fields(self):
		before = self.get_doc_before_save()
		if not before or not before.source_work_record_hash:
			return
		for fieldname in (
			"company",
			"payroll_frequency",
			"branch",
			"department",
			"start_date",
			"end_date",
			"payroll_date",
			"cost_center",
			"payroll_payable_account",
			"is_final_run_for_month",
		):
			if str(before.get(fieldname) or "") != str(self.get(fieldname) or ""):
				frappe.throw(
					_("{0} is locked because payroll source records have already been frozen.").format(
						self.meta.get_label(fieldname)
					)
				)

	def on_trash(self):
		if self.payroll_entry and frappe.db.exists("Payroll Entry", self.payroll_entry):
			frappe.throw(_("Delete or cancel the linked Payroll Entry before deleting this payroll run."))
		if self.employer_contribution_journal and frappe.db.exists("Journal Entry", self.employer_contribution_journal):
			frappe.throw(_("Cancel or delete the employer contribution Journal Entry before deleting this payroll run."))
		if frappe.db.exists(
			"Additional Salary",
			{"ref_doctype": self.doctype, "ref_docname": self.name, "docstatus": ["<", 2]},
		):
			frappe.throw(_("Cancel the linked Additional Salary records before deleting this payroll run."))
		if frappe.db.exists("Shift Work Record", {"payroll_run": self.name}):
			from malaysia_workforce.payroll.services import release_work_record_reservations

			release_work_record_reservations(self, reset_run=False)

	@frappe.whitelist(methods=["POST"])
	def collect_and_validate(self):
		from malaysia_workforce.payroll.services import collect_and_validate_run

		return collect_and_validate_run(self)

	@frappe.whitelist(methods=["POST"])
	def generate_additional_salaries(self):
		from malaysia_workforce.payroll.services import generate_additional_salaries

		return generate_additional_salaries(self)

	@frappe.whitelist(methods=["POST"])
	def create_payroll_entry(self):
		from malaysia_workforce.payroll.services import create_payroll_entry

		return create_payroll_entry(self)

	@frappe.whitelist(methods=["POST"])
	def create_missing_casual_assignments(self):
		from malaysia_workforce.payroll.services import create_missing_casual_assignments

		return create_missing_casual_assignments(self)

	@frappe.whitelist(methods=["POST"])
	def reset_generation(self):
		from malaysia_workforce.payroll.services import release_work_record_reservations

		return release_work_record_reservations(self)

	@frappe.whitelist(methods=["POST"])
	def create_employer_contribution_journal(self):
		from malaysia_workforce.payroll.services import create_employer_contribution_journal

		return create_employer_contribution_journal(self)

