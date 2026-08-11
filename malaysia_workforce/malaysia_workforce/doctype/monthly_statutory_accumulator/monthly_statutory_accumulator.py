from decimal import Decimal

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_first_day, getdate


class MonthlyStatutoryAccumulator(Document):
	def validate(self):
		self.contribution_month = get_first_day(self.contribution_month)
		if self.status in {"Submitted", "Reconciled"} and not self.is_new():
			before = self.get_doc_before_save()
			if before and before.status in {"Submitted", "Reconciled"} and self.as_dict() != before.as_dict():
				frappe.throw(_("Submitted statutory accumulators are immutable. Create an amendment instead."))
		for target, source in (("total_gross", "gross"), ("epf_wages", "epf_wages"), ("socso_wages", "socso_wages"), ("eis_wages", "eis_wages"), ("hrd_wages", "hrd_wages"), ("pcb_regular", "pcb_regular"), ("pcb_additional", "pcb_additional")):
			setattr(self, target, sum((Decimal(str(getattr(row, source) or 0)) for row in self.items), Decimal("0")))

	def on_trash(self):
		if not getattr(frappe.flags, "malaysia_accumulator_cleanup", False):
			frappe.throw(
				_("Statutory accumulators are derived audit records and may only be removed by a controlled Salary Slip cancellation.")
			)
