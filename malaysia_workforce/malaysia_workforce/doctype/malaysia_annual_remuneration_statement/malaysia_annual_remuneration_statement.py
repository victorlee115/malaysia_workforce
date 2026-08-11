import hashlib

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from malaysia_workforce.utils import ensure_roles


class MalaysiaAnnualRemunerationStatement(Document):
	def validate(self):
		self.revision = int(self.revision or 0)
		if self.revision < 0:
			frappe.throw(_("Revision cannot be negative."))
		self.statement_key = hashlib.sha256(
			f"{self.company}|{self.employee}|{self.tax_year}|{self.form_type}|{self.revision}".encode()
		).hexdigest()
		existing = frappe.db.get_value(
			"Malaysia Annual Remuneration Statement",
			{"statement_key": self.statement_key},
			"name",
		)
		if existing and existing != self.name:
			frappe.throw(_("This annual statement revision already exists: {0}.").format(existing))

		before = self.get_doc_before_save()
		if before and before.status in {"Issued", "Corrected"}:
			protected = (
				"employee",
				"company",
				"tax_year",
				"form_type",
				"revision",
				"statement_key",
				"gross_remuneration",
				"benefits_in_kind",
				"value_of_living_accommodation",
				"exempt_allowances",
				"epf_employee",
				"socso_employee",
				"eis_employee",
				"pcb",
				"cp38",
				"zakat",
				"issued_by",
				"issued_on",
				"generated_from_snapshot",
			)
			if any(str(before.get(fieldname) or "") != str(self.get(fieldname) or "") for fieldname in protected):
				frappe.throw(_("Issued annual statement data is immutable. Create the next revision."))
			if before.status == "Corrected" and self.status != "Corrected":
				frappe.throw(_("A corrected prior revision cannot be reopened."))
			if before.status == "Issued" and self.status not in {"Issued", "Corrected"}:
				frappe.throw(_("An issued statement can only be marked Corrected after a replacement is issued."))
			if before.status == "Issued" and self.status == "Corrected" and not frappe.db.exists(
				"Malaysia Annual Remuneration Statement",
				{
					"employee": self.employee,
					"company": self.company,
					"tax_year": self.tax_year,
					"form_type": self.form_type,
					"revision": [">", self.revision],
					"status": "Issued",
				},
			):
				frappe.throw(_("Issue a replacement revision before marking this statement Corrected."))
		if self.status == "Issued" and (not before or before.status != "Issued"):
			ensure_roles("HR Manager", "Malaysia HR Manager", "System Manager")
			self.issued_by = frappe.session.user
			self.issued_on = now_datetime()

	def on_trash(self):
		if self.status in {"Issued", "Corrected"}:
			frappe.throw(_("Issued or corrected annual statements cannot be deleted."))
