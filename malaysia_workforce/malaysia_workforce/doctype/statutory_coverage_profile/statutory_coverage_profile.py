from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime, today

from malaysia_workforce.data_access import get_work_agreement
from malaysia_workforce.utils import ensure_private_file, ensure_roles, stable_json, validate_date_range

SCHEMES = ("EPF", "SOCSO", "EIS", "PCB", "LINDUNG 24 Jam")


class StatutoryCoverageProfile(Document):
	def validate(self):
		validate_date_range(self.effective_from, self.effective_until, "statutory coverage profile")
		self._protect_relied_coverage()
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
		self._validate_exclusions()

	def _validate_overlap(self):
		this_start = getdate(self.effective_from)
		this_end = getdate(self.effective_until or "2999-12-31")
		for other in frappe.get_all(
			"Statutory Coverage Profile",
			filters={"employee": self.employee, "name": ["!=", self.name]},
			fields=["name", "effective_from", "effective_until"],
			limit=500,
		):
			other_start = getdate(other.effective_from)
			other_end = getdate(other.effective_until or "2999-12-31")
			if this_start <= other_end and other_start <= this_end:
				frappe.throw(_("Statutory Coverage Profile {0} overlaps this effective period.").format(other.name))

	def _validate_exclusions(self):
		if not any(line.treatment == "Not Applicable" for line in self.coverage_lines):
			self.exclusion_approved_by = None
			self.exclusion_approved_on = None
			return
		ensure_roles("HR Manager", "Malaysia HR Manager", "System Manager")
		if not self.exclusion_approval_evidence:
			frappe.throw(_("Attach approval evidence before marking a statutory scheme Not Applicable."))
		self.exclusion_approval_evidence = ensure_private_file(
			self.exclusion_approval_evidence,
			_("Statutory exclusion approval evidence"),
		)
		for line in self.coverage_lines:
			if line.treatment == "Not Applicable" and (not line.reason_code or not (line.notes or "").strip()):
				frappe.throw(_("{0}: a controlled reason and detailed notes are required for Not Applicable.").format(line.scheme))
		agreement = get_work_agreement(self.employee, self.effective_from)
		if agreement and agreement.get("contract_relationship") == "Contract of Service":
			frappe.msgprint(
				_("The recorded statutory exclusion will be retained with HR Manager evidence and immutable history."),
				indicator="orange",
				alert=True,
			)
		before = self.get_doc_before_save()
		before_treatments = (
			{row.scheme: row.treatment for row in before.coverage_lines} if before else {}
		)
		current_treatments = {row.scheme: row.treatment for row in self.coverage_lines}
		if (
			before
			and before.exclusion_approval_evidence == self.exclusion_approval_evidence
			and before_treatments == current_treatments
			and before.exclusion_approved_by
		):
			self.exclusion_approved_by = before.exclusion_approved_by
			self.exclusion_approved_on = before.exclusion_approved_on
		else:
			self.exclusion_approved_by = frappe.session.user
			self.exclusion_approved_on = now_datetime()

	def _protect_relied_coverage(self):
		before = self.get_doc_before_save()
		if not before:
			return

		def payload(doc, *, ignore_end=False):
			return stable_json(
				{
					"employee": doc.employee,
					"company": doc.company,
					"effective_from": doc.effective_from,
					"effective_until": None if ignore_end else doc.effective_until,
					"evidence": doc.exclusion_approval_evidence,
					"lines": [
						{
							"scheme": row.scheme,
							"treatment": row.treatment,
							"reason_code": row.reason_code,
							"notes": row.notes,
							"effective_from": row.effective_from,
							"effective_until": None if ignore_end else row.effective_until,
						}
						for row in doc.coverage_lines
					],
				}
			)

		if payload(before) == payload(self):
			return
		latest = frappe.get_all(
			"Salary Slip",
			filters={
				"employee": self.employee,
				"docstatus": 1,
				"start_date": ["<=", before.effective_until or "2999-12-31"],
				"end_date": [">=", before.effective_from],
				"custom_malaysia_statutory_snapshot": ["is", "set"],
			},
			fields=["end_date"],
			order_by="end_date desc",
			limit=1,
		)
		if not latest:
			return
		if (
			payload(before, ignore_end=True) == payload(self, ignore_end=True)
			and self.effective_until
			and getdate(self.effective_until) >= getdate(latest[0].end_date)
		):
			return
		frappe.throw(
			_("This coverage profile has been relied upon by payroll. End-date it after the latest relied period and create a new effective-dated profile.")
		)

	def on_trash(self):
		if frappe.db.exists("Statutory Treatment History", {"profile": self.name}):
			frappe.throw(_("A relied-upon coverage profile cannot be deleted. End-date it and create a replacement."))

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
			limit=1000,
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
			history.snapshot = json.dumps(
				{
					"coverage_line": line.as_dict(),
					"exclusion_approval_evidence": self.exclusion_approval_evidence,
					"exclusion_approved_by": self.exclusion_approved_by,
					"exclusion_approved_on": self.exclusion_approved_on,
				},
				default=str,
				sort_keys=True,
			)
			history.insert(ignore_permissions=True)
