from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from malaysia_workforce.staffing.intervals import coerce_time
from malaysia_workforce.utils import validate_date_range


def _minutes(value) -> int:
	parsed = coerce_time(value)
	return parsed.hour * 60 + parsed.minute


class CafeCoverageTemplate(Document):
	def validate(self):
		validate_date_range(self.effective_from, self.effective_until, "coverage template")
		if self.branch:
			branch_company = frappe.db.get_value("Branch", self.branch, "company")
			if branch_company and branch_company != self.company:
				frappe.throw(_("Branch belongs to another Company."))
		if not self.coverage_rows:
			frappe.throw(_("Add at least one weekly coverage row."))
		seen = []
		for row in self.coverage_rows:
			start = _minutes(row.start_time)
			end = _minutes(row.end_time)
			if start % 30 or end % 30:
				frappe.throw(_("Coverage times must use 30-minute boundaries."))
			if end <= start:
				frappe.throw(_("Coverage row {0} must end after it starts.").format(row.idx))
			if int(row.required_headcount or 0) < 1:
				frappe.throw(_("Coverage row {0} requires at least one employee.").format(row.idx))
			key = (row.weekday, row.designation or "", row.required_skill or "")
			for other_key, other_start, other_end in seen:
				if key == other_key and start < other_end and other_start < end:
					frappe.throw(_("Overlapping coverage rows for {0} would double-count demand.").format(row.weekday))
			seen.append((key, start, end))
		self._protect_used_template()

	def _protect_used_template(self):
		before = self.get_doc_before_save()
		if not before or before.as_dict() == self.as_dict():
			return
		if frappe.db.exists(
			"Cafe Staffing Plan", {"coverage_template": self.name, "workflow_state": ["in", ["Approved", "Superseded"]]}
		):
			frappe.throw(_("This template has an approved staffing plan. Create a new effective-dated template."))

	def on_trash(self):
		if frappe.db.exists("Cafe Staffing Plan", {"coverage_template": self.name, "docstatus": ["<", 2]}):
			frappe.throw(_("This template is referenced by a staffing plan."))
