from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime, today

from malaysia_workforce.data_access import get_work_agreement
from malaysia_workforce.utils import validate_date_range

SCHEMES = ("EPF", "SOCSO", "EIS", "PCB", "LINDUNG 24 Jam")


class StatutoryCoverageProfile(Document):
	def validate(self):
		validate_date_range(self.effective_from, self.effective_until, "statutory coverage profile")
		employee_company = frappe.db.get_value("Employee", self.employee, "company")
		if employee_company and self.company != employee_company:
			frappe.throw(_("Statutory Coverage Profile company must match the Employee company."))
		self._validate_overlap()
		if not self.coverage_lines:
			for scheme in SCHEMES:
				self.append(
					"coverage_lines",
					{"scheme": scheme, "treatment": "Automatic", "effective_from": self.effective_from},
				)

		seen: set[str] = set()
		for line in self.coverage_lines:
			if line.scheme not in SCHEMES:
				frappe.throw(_("Unsupported statutory scheme: {0}.").format(line.scheme))
			if line.scheme in seen:
				frappe.throw(_("Only one coverage line is allowed for {0} in a profile.").format(line.scheme))
			seen.add(line.scheme)
			line.effective_from = line.effective_from or self.effective_from
			line.effective_until = line.effective_until or self.effective_until
			validate_date_range(line.effective_from, line.effective_until, line.scheme)
			if getdate(line.effective_from) < getdate(self.effective_from):
				frappe.throw(_("{0} cannot start before the profile effective date.").format(line.scheme))
			if self.effective_until and (
				not line.effective_until or getdate(line.effective_until) > getdate(self.effective_until)
			):
				frappe.throw(_("{0} cannot end after the profile effective period.").format(line.scheme))

		for scheme in SCHEMES:
			if scheme not in seen:
				self.append(
					"coverage_lines",
					{
						"scheme": scheme,
						"treatment": "Automatic",
						"effective_from": self.effective_from,
						"effective_until": self.effective_until,
					},
				)
		self.last_reviewed_on = today()
		self._warn_on_exclusions()

	def _validate_overlap(self):
		this_start = getdate(self.effective_from)
		this_end = getdate(self.effective_until or "2999-12-31")
		for other in frappe.get_all(
			"Statutory Coverage Profile",
			filters={"employee": self.employee, "name": ["!=", self.name]},
			fields=["name", "effective_from", "effective_until"],
			limit_page_length=500,
		):
			other_start = getdate(other.effective_from)
			other_end = getdate(other.effective_until or "2999-12-31")
			if this_start <= other_end and other_start <= this_end:
				frappe.throw(_("Statutory Coverage Profile {0} overlaps this effective period.").format(other.name))

	def _warn_on_exclusions(self):
		if not any(line.treatment == "Not Applicable" for line in self.coverage_lines):
			return
		agreement = get_work_agreement(self.employee, self.effective_from)
		if agreement and agreement.get("contract_relationship") == "Contract of Service":
			frappe.msgprint(
				_(
					"One or more schemes are marked Not Applicable while the current work agreement is a "
					"Contract of Service. The setting will still save immediately, as requested, and the "
					"change will be retained in the immutable treatment history."
				),
				indicator="orange",
				alert=True,
			)

	def on_update(self):
		self._write_history()
		today_date = getdate(today())
		if getdate(self.effective_from) <= today_date <= getdate(self.effective_until or "2999-12-31"):
			frappe.db.set_value(
				"Employee",
				self.employee,
				"custom_statutory_coverage_profile",
				self.name,
				update_modified=False,
			)
		for salary_slip in frappe.get_all(
			"Salary Slip",
			filters={"employee": self.employee, "docstatus": 0},
			pluck="name",
			limit_page_length=1000,
		):
			frappe.db.set_value(
				"Salary Slip",
				salary_slip,
				"custom_statutory_recalculation_required",
				1,
				update_modified=False,
			)

	def _write_history(self):
		before = self.get_doc_before_save()
		old = {line.scheme: line.as_dict() for line in before.coverage_lines} if before else {}
		for line in self.coverage_lines:
			previous = old.get(line.scheme, {})
			comparison_fields = ("treatment", "reason_code", "notes", "effective_from", "effective_until")
			if all(str(previous.get(fieldname) or "") == str(line.get(fieldname) or "") for fieldname in comparison_fields):
				continue
			history = frappe.new_doc("Statutory Treatment History")
			history.employee = self.employee
			history.profile = self.name
			history.scheme = line.scheme
			history.previous_treatment = previous.get("treatment", "")
			history.new_treatment = line.treatment
			history.effective_from = line.effective_from or self.effective_from
			history.changed_by = frappe.session.user
			history.changed_on = now_datetime()
			history.reason = " – ".join(filter(None, [line.reason_code, line.notes]))
			history.snapshot = json.dumps(line.as_dict(), default=str, sort_keys=True)
			history.insert(ignore_permissions=True)
