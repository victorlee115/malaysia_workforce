import frappe
from frappe import _
from frappe.model.document import Document


class StatutoryTreatmentHistory(Document):
	def before_save(self):
		if not self.is_new():
			frappe.throw(_("Statutory Treatment History is immutable."))

	def on_trash(self):
		frappe.throw(_("Statutory Treatment History cannot be deleted."))
