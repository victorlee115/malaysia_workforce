from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime

from malaysia_workforce.utils import stable_json

MONTHLY_TYPES = {"Monthly PCB", "EPF Form A", "SOCSO EIS Combined"}
ANNUAL_TYPES = {"CP8D Preparation", "Form E Preparation"}
AUTHORITY_TYPES = {
	"LHDN": {"Monthly PCB", "CP8D Preparation", "Form E Preparation", "Employee Notification", "Annual Statement"},
	"EPF": {"EPF Form A"},
	"PERKESO": {"SOCSO EIS Combined"},
}
FROZEN_STATUSES = {"Submitted", "Accepted", "Rejected", "Paid", "Reconciled"}


def _amount(value, label: str) -> Decimal:
	try:
		amount = Decimal(str(value or 0))
	except (InvalidOperation, TypeError, ValueError) as exc:
		frappe.throw(_("{0} must be a valid amount.").format(label))
		raise AssertionError from exc
	if not amount.is_finite() or amount < 0:
		frappe.throw(_("{0} must be a finite, non-negative amount.").format(label))
	return amount


def _canonical_lines(lines) -> str:
	return stable_json(
		[
			{
				key: value
				for key, value in row.as_dict().items()
				if key not in {"name", "owner", "creation", "modified", "modified_by", "parent", "parentfield", "parenttype", "idx", "doctype"}
			}
			for row in lines
		]
	)


class StatutorySubmission(Document):
	def validate(self):
		self._validate_period_and_type()
		self._validate_unique_revision()
		self._protect_submitted_source()
		self._calculate_totals()
		self._validate_status_requirements()

	def _validate_period_and_type(self):
		if self.authority not in AUTHORITY_TYPES or self.submission_type not in AUTHORITY_TYPES[self.authority]:
			frappe.throw(_("Submission Type {0} is not valid for authority {1}.").format(self.submission_type, self.authority))
		if int(self.contribution_year or 0) < 2000 or int(self.contribution_year or 0) > getdate().year + 1:
			frappe.throw(_("Contribution Year must be between 2000 and {0}.").format(getdate().year + 1))
		if self.submission_type in MONTHLY_TYPES:
			if not self.contribution_month or not 1 <= int(self.contribution_month) <= 12:
				frappe.throw(_("Contribution Month must be between 1 and 12."))
		elif self.submission_type in ANNUAL_TYPES:
			self.contribution_month = None
		if int(self.revision or 0) < 0:
			frappe.throw(_("Revision cannot be negative."))

	def _validate_unique_revision(self):
		filters = {
			"company": self.company,
			"authority": self.authority,
			"submission_type": self.submission_type,
			"contribution_year": self.contribution_year,
			"revision": int(self.revision or 0),
		}
		filters["contribution_month"] = int(self.contribution_month) if self.contribution_month else ["is", "not set"]
		existing = frappe.db.get_value("Statutory Submission", filters, "name")
		if existing and existing != self.name:
			frappe.throw(
				_("Submission revision already exists: {0}. Open it or create the next revision.").format(existing)
			)

	def _protect_submitted_source(self):
		before = self.get_doc_before_save()
		if not before or before.status not in FROZEN_STATUSES:
			return
		protected = (
			"company",
			"authority",
			"submission_type",
			"contribution_year",
			"contribution_month",
			"revision",
			"submission_mode",
			"payroll_run",
			"schema_version",
			"generated_file",
			"file_sha256",
			"source_snapshot_hash",
			"source_salary_slips",
			"employer_reference_snapshot",
		)
		for fieldname in protected:
			if str(before.get(fieldname) or "") != str(self.get(fieldname) or ""):
				frappe.throw(_("Submitted source field {0} is immutable. Create a new revision.").format(self.meta.get_label(fieldname)))
		if _canonical_lines(before.employee_lines) != _canonical_lines(self.employee_lines):
			frappe.throw(_("Submitted employee lines are immutable. Create a new revision."))

	def _calculate_totals(self):
		seen_employees: set[str] = set()
		amount_fields = (
			"wages",
			"employee_amount",
			"employer_amount",
			"extra_employee_amount",
			"mtd_amount",
			"cp38_amount",
		)
		for row in self.employee_lines:
			if not row.employee:
				frappe.throw(_("Every statutory submission line must reference an Employee."))
			if row.employee in seen_employees:
				frappe.throw(_("Employee {0} appears more than once in this submission.").format(row.employee))
			seen_employees.add(row.employee)
			for fieldname in amount_fields:
				_amount(row.get(fieldname), _("Row {0}: {1}").format(row.idx, row.meta.get_label(fieldname)))
		self.employee_count = len(self.employee_lines)
		self.wage_total = sum((_amount(row.wages, _("Wages")) for row in self.employee_lines), Decimal("0"))
		self.employee_contribution_total = sum(
			(_amount(row.employee_amount, _("Employee Contribution")) for row in self.employee_lines), Decimal("0")
		)
		self.employer_contribution_total = sum(
			(_amount(row.employer_amount, _("Employer Contribution")) for row in self.employee_lines), Decimal("0")
		)
		self.extra_employee_total = sum(
			(_amount(row.extra_employee_amount, _("Extra Employee Contribution")) for row in self.employee_lines), Decimal("0")
		)
		if self.submission_type == "Monthly PCB":
			self.payable_total = sum(
				(_amount(row.mtd_amount, _("MTD Amount")) + _amount(row.cp38_amount, _("CP38 Amount")) for row in self.employee_lines),
				Decimal("0"),
			)
		else:
			self.payable_total = (
				self.employee_contribution_total
				+ self.employer_contribution_total
				+ self.extra_employee_total
			)
		if self.paid_amount not in (None, ""):
			self.reconciliation_difference = _amount(self.paid_amount, _("Paid Amount")) - Decimal(
				str(self.payable_total or 0)
			)

	def _validate_status_requirements(self):
		if self.status in {"Generated", "Ready for Portal", "Submitted", "Accepted", "Paid", "Reconciled"}:
			if not self.generated_file and self.submission_type in MONTHLY_TYPES:
				frappe.throw(_("A generated authority file is required for this status."))
			if self.generated_file and not self.file_sha256:
				frappe.throw(_("Generated File SHA-256 is required."))
		if self.status in {"Submitted", "Accepted", "Paid", "Reconciled"}:
			if not self.external_reference or not self.submitted_on:
				frappe.throw(_("External Reference and Submitted On are required after submission."))
		if self.status in {"Paid", "Reconciled"}:
			if not self.payment_reference or not self.paid_on or self.paid_amount in (None, ""):
				frappe.throw(_("Payment Reference, Paid On and Paid Amount are required."))
		if self.status == "Reconciled" and abs(Decimal(str(self.reconciliation_difference or 0))) > Decimal("0.01"):
			frappe.throw(_("A submission cannot be Reconciled while the payment difference is non-zero."))

	def on_trash(self):
		if self.status not in {"Draft", "Validation Failed"}:
			frappe.throw(_("Only draft or validation-failed submissions can be deleted."))

	@frappe.whitelist(methods=["POST"])
	def generate_file(self):
		self.check_permission("write")
		from malaysia_workforce.statutory.submission_service import generate_submission_file

		return generate_submission_file(self)

	@frappe.whitelist(methods=["POST"])
	def load_from_payroll(self):
		self.check_permission("write")
		from malaysia_workforce.statutory.submission_service import populate_submission_lines

		return populate_submission_lines(self)

	@frappe.whitelist(methods=["POST"])
	def mark_submitted(self, external_reference: str, acknowledgement: str | None = None):
		self.check_permission("write")
		if self.submission_type == "EPF Form A" and str(self.schema_version or "").startswith(
			"KWSP-ECARUMAN-LEGACY"
		):
			frappe.throw(
				_(
					"A legacy e-Caruman UAT file cannot be marked as an official EPF submission. "
					"Use a verified current i-Akaun (Employer) workflow and retain its acknowledgement."
				),
				title=_("Unverified EPF Submission Format"),
			)
		if self.status not in {"Generated", "Ready for Portal"}:
			frappe.throw(_("Generate and validate the file before marking it submitted."))
		if not external_reference or not str(external_reference).strip():
			frappe.throw(_("External Reference is required."))
		self.external_reference = str(external_reference).strip()
		if acknowledgement:
			self.acknowledgement = acknowledgement
		self.submitted_on = now_datetime()
		self.status = "Submitted"
		self.save()
		return self.name

	@frappe.whitelist(methods=["POST"])
	def mark_accepted(self, acknowledgement: str | None = None):
		self.check_permission("write")
		if self.status not in {"Submitted", "Accepted"}:
			frappe.throw(_("Only a submitted record can be marked Accepted."))
		if acknowledgement:
			self.acknowledgement = acknowledgement
		self.accepted_on = now_datetime()
		self.status = "Accepted"
		self.save()
		return self.name

	@frappe.whitelist(methods=["POST"])
	def mark_rejected(self, reason: str):
		self.check_permission("write")
		if self.status not in {"Submitted", "Ready for Portal", "Generated"}:
			frappe.throw(_("This record cannot be marked Rejected from its current status."))
		if not reason or not str(reason).strip():
			frappe.throw(_("A rejection reason is required."))
		self.validation_errors = json.dumps([str(reason).strip()], indent=2)
		self.status = "Rejected"
		self.save()
		return self.name

	@frappe.whitelist(methods=["POST"])
	def mark_paid(self, payment_reference: str, paid_amount, receipt: str | None = None):
		self.check_permission("write")
		if self.status not in {"Submitted", "Accepted", "Paid"}:
			frappe.throw(_("Only a submitted or accepted record can be marked Paid."))
		if not payment_reference or not str(payment_reference).strip():
			frappe.throw(_("Payment Reference is required."))
		amount = _amount(paid_amount, _("Paid Amount"))
		self.payment_reference = str(payment_reference).strip()
		self.paid_amount = amount
		if receipt:
			self.receipt = receipt
		self.paid_on = now_datetime()
		self.status = "Paid"
		self.save()
		return self.name

	@frappe.whitelist(methods=["POST"])
	def reconcile(self):
		self.check_permission("write")
		if self.status not in {"Paid", "Reconciled"}:
			frappe.throw(_("Record payment before reconciliation."))
		self._calculate_totals()
		if abs(Decimal(str(self.reconciliation_difference or 0))) > Decimal("0.01"):
			frappe.throw(
				_("Payment differs from the authority payable total by RM {0}.").format(self.reconciliation_difference)
			)
		self.reconciled_on = now_datetime()
		self.status = "Reconciled"
		self.save()
		return self.name
