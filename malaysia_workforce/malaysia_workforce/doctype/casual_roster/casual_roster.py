from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, getdate, now_datetime

from malaysia_workforce.permissions import is_roster_admin, is_roster_manager
from malaysia_workforce.roster.services import build_coverage_grid
from malaysia_workforce.utils import validate_date_range, validate_decimal


class CasualRoster(Document):
	def validate(self):
		if is_roster_manager() and not is_roster_admin():
			if self.is_new() and not self.manager:
				self.manager = frappe.session.user
			if self.manager != frappe.session.user:
				frappe.throw(_("Roster Managers may only create or maintain rosters assigned to themselves."), frappe.PermissionError)
		validate_date_range(self.start_date, self.end_date, "roster")
		if self.application_opens and self.application_closes and get_datetime(
			self.application_closes
		) <= get_datetime(self.application_opens):
			frappe.throw(_("Applications Close must be after Applications Open."))
		if self.application_closes and self.selection_deadline and get_datetime(
			self.selection_deadline
		) < get_datetime(self.application_closes):
			frappe.throw(_("Selection Deadline cannot be before Applications Close."))
		if not self.coverage_requirements:
			frappe.throw(_("Add at least one coverage requirement."))
		if len(self.coverage_requirements) > 1000:
			frappe.throw(_("A roster cannot contain more than 1,000 coverage rows."))
		if self.project:
			project_company = frappe.db.get_value("Project", self.project, "company")
			if project_company and project_company != self.company:
				frappe.throw(_("Project {0} does not belong to company {1}.").format(self.project, self.company))
		if self.branch:
			branch_company = frappe.db.get_value("Branch", self.branch, "company")
			if branch_company and branch_company != self.company:
				frappe.throw(_("Branch {0} does not belong to company {1}.").format(self.branch, self.company))
		settings = frappe.get_cached_doc("Malaysia Workforce Settings")
		for row in self.coverage_requirements:
			if not getdate(self.start_date) <= getdate(row.work_date) <= getdate(self.end_date):
				frappe.throw(_("Coverage date {0} is outside the roster date range.").format(row.work_date))
			role = (row.role or "").strip()
			if not role:
				frappe.throw(_("Coverage row {0} requires a role.").format(row.idx))
			if len(role) > 140:
				frappe.throw(_("Coverage row {0} role cannot exceed 140 characters.").format(row.idx))
			row.role = role
			headcount = validate_decimal(
				row.required_headcount, _("Required Headcount"), minimum=1, maximum=10000, allow_blank=False
			)
			if headcount != int(headcount):
				frappe.throw(_("Required Headcount must be a whole number."))
			rate = validate_decimal(row.hourly_rate, _("Hourly Rate"), minimum=0)
			if (
				row.hourly_rate
				and settings.minimum_wage_effective_from
				and getdate(row.work_date) >= getdate(settings.minimum_wage_effective_from)
				and rate < validate_decimal(settings.minimum_hourly_rate, _("Minimum Hourly Rate"), minimum=0, allow_blank=False)
			):
				frappe.throw(
					_("Coverage row {0} uses an hourly rate below the configured minimum.").format(row.idx)
				)
			if row.cost_center:
				cc_company = frappe.db.get_value("Cost Center", row.cost_center, "company")
				if cc_company and cc_company != self.company:
					frappe.throw(_("Coverage row {0} Cost Center belongs to another company.").format(row.idx))
			if row.project:
				project_company = frappe.db.get_value("Project", row.project, "company")
				if project_company and project_company != self.company:
					frappe.throw(_("Coverage row {0} Project belongs to another company.").format(row.idx))
		self._prevent_published_structure_changes()

	def _prevent_published_structure_changes(self):
		before = self.get_doc_before_save()
		if not before or before.status not in {"Published", "In Progress", "Completed", "Payroll Ready", "Closed"}:
			return
		locked_fields = (
			"company",
			"start_date",
			"end_date",
			"default_shift_location",
			"project",
		)
		if any(str(before.get(fieldname) or "") != str(self.get(fieldname) or "") for fieldname in locked_fields):
			frappe.throw(_("Published roster structure is locked. Cancel affected selections before changing it."))
		coverage_fields = (
			"work_date",
			"start_time",
			"end_time",
			"role",
			"required_headcount",
			"hourly_rate",
			"required_skill",
			"shift_location",
			"cost_center",
			"project",
		)
		def frozen_rows(rows):
			return [
				{fieldname: str(row.get(fieldname) or "") for fieldname in coverage_fields}
				for row in rows
			]

		before_coverage = json.dumps(frozen_rows(before.coverage_requirements), sort_keys=True)
		current_coverage = json.dumps(frozen_rows(self.coverage_requirements), sort_keys=True)
		if before_coverage != current_coverage:
			frappe.throw(_("Coverage requirements cannot be changed after the roster is published."))

	@frappe.whitelist(methods=["POST"])
	def open_for_applications(self):
		self.check_permission("write")
		if self.status not in {"Draft", "Applications Closed"}:
			frappe.throw(_("This roster cannot be opened from status {0}.").format(self.status))
		self.status = "Open for Applications"
		self.application_opens = self.application_opens or now_datetime()
		self.save()
		return self.name

	@frappe.whitelist(methods=["POST"])
	def close_applications(self):
		self.check_permission("write")
		if self.status not in {"Open for Applications", "Applications Closed", "Selecting"}:
			frappe.throw(_("Applications cannot be closed from status {0}.").format(self.status))
		self.status = "Applications Closed" if not frappe.db.exists(
			"Roster Selection", {"roster": self.name, "docstatus": ["<", 2], "status": ["!=", "Declined"]}
		) else "Selecting"
		self.application_closes = self.application_closes or now_datetime()
		self.save()
		return self.name

	@frappe.whitelist(methods=["POST"])
	def publish_roster(self, allow_gaps: int = 0):
		self.check_permission("write")
		if self.status in {"Published", "In Progress", "Completed", "Payroll Ready", "Closed"}:
			return {"name": self.name, "status": self.status, "already_published": True}
		selections = frappe.get_all(
			"Roster Selection",
			filters={"roster": self.name, "docstatus": ["<", 2], "status": ["!=", "Declined"]},
			fields=["name", "docstatus"],
			order_by="work_date, selected_from, creation",
			limit_page_length=10000,
		)
		if not selections:
			frappe.throw(_("Select at least one worker before publishing the roster."))
		pending_confirmations = frappe.get_all(
			"Roster Selection",
			filters={
				"roster": self.name,
				"docstatus": 0,
				"employee_confirmation_status": "Pending",
			},
			pluck="name",
			limit_page_length=10000,
		)
		if pending_confirmations:
			frappe.throw(
				_("{0} selected worker(s) must confirm their exact hours before publication.").format(
					len(pending_confirmations)
				)
			)
		coverage = build_coverage_grid(self.name)
		unfilled_slots = [row for row in coverage if int(row.get("gap") or 0) > 0]
		if unfilled_slots and not int(allow_gaps or 0):
			frappe.throw(
				_("The roster still has {0} uncovered role/time slots. Publish again with Allow Gaps enabled to continue.").format(
					len(unfilled_slots)
				)
			)
		for row in selections:
			if int(row.docstatus) == 0:
				frappe.get_doc("Roster Selection", row.name).submit()
		selected_applications = set(
			frappe.get_all(
				"Roster Selection",
				filters={"roster": self.name, "docstatus": 1},
				pluck="application",
				limit_page_length=10000,
			)
		)
		for application in frappe.get_all(
			"Roster Application",
			filters={"roster": self.name, "status": ["in", ["Applied", "Selected"]]},
			fields=["name"],
			limit_page_length=10000,
		):
			frappe.db.set_value(
				"Roster Application",
				application.name,
				"status",
				"Selected" if application.name in selected_applications else "Not Selected",
				update_modified=False,
			)
		self.status = "Published"
		self.application_closes = self.application_closes or now_datetime()
		self.save()
		frappe.publish_realtime(
			"malaysia_workforce:roster_published",
			{"roster": self.name, "selection_count": len(selections)},
			after_commit=True,
		)
		return {
			"name": self.name,
			"status": self.status,
			"selection_count": len(selections),
			"unfilled_slot_count": len(unfilled_slots),
		}
