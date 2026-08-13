import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime


class MalaysiaStatutoryFiling(Document):
	def validate(self):
		if getdate(self.period_end) < getdate(self.period_start):
			frappe.throw(_("Period End cannot be before Period Start."))
		duplicate = frappe.db.get_value(
			"Malaysia Statutory Filing",
			{
				"company": self.company,
				"authority": self.authority,
				"period_start": self.period_start,
				"period_end": self.period_end,
				"docstatus": ["<", 2],
				"name": ["!=", self.name],
			},
			"name",
		)
		if duplicate:
			frappe.throw(_("An active filing already exists for this authority and period: {0}.").format(duplicate))
		if self.docstatus == 1 and self.authority_status == "Accepted" and not self.acknowledgement:
			frappe.throw(_("Attach the authority acknowledgement before marking this filing Accepted."))

	def before_submit(self):
		if not (self.generated_file and self.source_hash and self.file_hash):
			frappe.throw(_("Prepare the filing output before submission."))
		if not self.submission_evidence:
			frappe.throw(_("Attach the portal receipt or submission evidence before submission."))
		from malaysia_workforce.statutory.filing import validate_filing_source

		validate_filing_source(self)
		self.authority_status = "Pending"
		self.reconciliation_status = "Not Reconciled"
		self.submitted_by = frappe.session.user
		self.submitted_at = now_datetime()

	@frappe.whitelist()
	def prepare(self):
		from malaysia_workforce.statutory.filing import prepare_filing

		return prepare_filing(self)

	@frappe.whitelist()
	def reconcile(self):
		from malaysia_workforce.statutory.filing import reconcile_filing

		return reconcile_filing(self)
