from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, getdate, now_datetime

from malaysia_workforce.data_access import get_work_agreement
from malaysia_workforce.permissions import is_privileged
from malaysia_workforce.roster.input_validation import (
	boolean_flag,
	validate_application_inputs,
	validate_preferred_role,
	validate_availability_rows,
)
from malaysia_workforce.roster.services import build_coverage_grid, recommend_for_requirement
from malaysia_workforce.utils import ensure_roles, get_current_employee


def _parse_windows(value) -> list[dict]:
	rows = frappe.parse_json(value) if isinstance(value, str) else value
	try:
		return validate_availability_rows(rows)
	except ValueError as exc:
		frappe.throw(_(str(exc)))



@frappe.whitelist()
def get_employee_dashboard():
	employee = get_current_employee()
	employee_row = frappe.db.get_value(
		"Employee", employee, ["company", "custom_roster_enabled"], as_dict=True
	)
	if not employee_row:
		frappe.throw(_("No active Employee record is linked to this user."), frappe.PermissionError)
	now = now_datetime()
	open_rosters = []
	if employee_row.custom_roster_enabled:
		for roster in frappe.get_all(
			"Casual Roster",
			filters={
				"company": employee_row.company,
				"status": "Open for Applications",
				"end_date": [">=", getdate()],
			},
			fields=[
				"name",
				"roster_title",
				"company",
				"start_date",
				"end_date",
				"application_opens",
				"application_closes",
				"default_shift_location",
			],
			order_by="start_date asc",
			limit_page_length=100,
		):
			if roster.application_opens and now < get_datetime(roster.application_opens):
				continue
			if roster.application_closes and now > get_datetime(roster.application_closes):
				continue
			open_rosters.append(roster)
	applications = frappe.get_all(
		"Roster Application",
		filters={"employee": employee, "status": ["!=", "Withdrawn"]},
		fields=["name", "roster", "status", "applied_on", "preferred_role"],
		order_by="modified desc",
		limit_page_length=100,
	)
	pending_offers = frappe.get_all(
		"Roster Selection",
		filters={
			"employee": employee,
			"docstatus": 0,
			"employee_confirmation_status": "Pending",
			"work_date": [">=", getdate()],
		},
		fields=[
			"name",
			"roster",
			"work_date",
			"selected_from",
			"selected_until",
			"assigned_role",
			"hourly_rate",
			"shift_location",
		],
		order_by="work_date asc, selected_from asc",
		limit_page_length=100,
	)
	confirmed = frappe.get_all(
		"Roster Selection",
		filters={"employee": employee, "docstatus": 1, "work_date": [">=", getdate()]},
		fields=[
			"name",
			"roster",
			"work_date",
			"selected_from",
			"selected_until",
			"assigned_role",
			"hourly_rate",
			"shift_location",
			"shift_work_record",
		],
		order_by="work_date asc, selected_from asc",
		limit_page_length=100,
	)
	return {
		"employee": employee,
		"open_rosters": open_rosters,
		"applications": applications,
		"pending_offers": pending_offers,
		"confirmed": confirmed,
	}


@frappe.whitelist()
def get_roster_details(roster: str):
	doc = frappe.get_doc("Casual Roster", roster)
	doc.check_permission("read")
	if not is_privileged():
		employee = get_current_employee()
		if frappe.db.get_value("Employee", employee, "company") != doc.company:
			frappe.throw(_("This roster belongs to a different company."), frappe.PermissionError)
	return {
		"roster": doc.as_dict(),
		"coverage": build_coverage_grid(roster),
		"allow_split_shifts": bool(
			cint(frappe.db.get_single_value("HR Settings", "allow_multiple_shift_assignments"))
		),
	}


@frappe.whitelist(methods=["POST"])
def submit_application(
	roster: str,
	availability_windows,
	preferred_role: str | None = None,
	minimum_shift_hours: float | None = None,
	maximum_hours: float | None = None,
	split_shifts_allowed: int = 0,
	commitment_type: str = "Manager may assign any hours inside my availability",
	employee_notes: str | None = None,
):
	employee = get_current_employee()
	if not frappe.db.get_value("Employee", employee, "custom_roster_enabled"):
		frappe.throw(_("Your Employee record is not enabled for casual rosters."))
	roster_doc = frappe.get_doc("Casual Roster", roster)
	employee_company = frappe.db.get_value("Employee", employee, "company")
	if roster_doc.company != employee_company:
		frappe.throw(_("This roster belongs to a different company."), frappe.PermissionError)
	if roster_doc.status != "Open for Applications":
		frappe.throw(_("This roster is not open for applications."))
	if roster_doc.application_closes and now_datetime() > get_datetime(roster_doc.application_closes):
		frappe.throw(_("Applications have closed."))
	name = frappe.db.get_value(
		"Roster Application", {"roster": roster, "employee": employee}, "name"
	)
	doc = frappe.get_doc("Roster Application", name) if name else frappe.new_doc("Roster Application")
	if name and frappe.db.exists("Roster Selection", {"application": name, "docstatus": ["<", 2], "status": ["!=", "Declined"]}):
		frappe.throw(_("This application already has a confirmed selection."))
	if not name:
		doc.roster = roster
		doc.employee = employee
		doc.company = roster_doc.company
	doc.status = "Applied"
	try:
		application_values = validate_application_inputs(
			minimum_shift_hours=minimum_shift_hours,
			maximum_hours=maximum_hours,
			split_shifts_allowed=split_shifts_allowed,
			commitment_type=commitment_type,
			employee_notes=employee_notes,
		)
	except ValueError as exc:
		frappe.throw(_(str(exc)))
	doc.preferred_role = validate_preferred_role(preferred_role)
	for fieldname, value in application_values.items():
		doc.set(fieldname, value)
	doc.set("availability_windows", [])
	for row in _parse_windows(availability_windows):
		doc.append("availability_windows", row)
	doc.save(ignore_permissions=True)
	return {"name": doc.name, "status": doc.status}


@frappe.whitelist(methods=["POST"])
def withdraw_application(application: str):
	employee = get_current_employee()
	doc = frappe.get_doc("Roster Application", application)
	if doc.employee != employee:
		frappe.throw(_("You can only withdraw your own application."), frappe.PermissionError)
	if doc.status == "Selected" or frappe.db.exists("Roster Selection", {"application": doc.name, "docstatus": ["<", 2], "status": ["!=", "Declined"]}):
		frappe.throw(_("You have already been selected. Use the shift withdrawal process instead."))
	doc.status = "Withdrawn"
	doc.save(ignore_permissions=True)
	return {"name": doc.name, "status": doc.status}


@frappe.whitelist()
def manager_roster(roster: str):
	ensure_roles("Roster Manager", "HR Manager", "Malaysia HR Manager", "System Manager")
	doc = frappe.get_doc("Casual Roster", roster)
	doc.check_permission("read")
	applications = frappe.get_all(
		"Roster Application",
		filters={"roster": roster, "status": ["in", ["Applied", "Standby", "Selected"]]},
		fields=["name", "employee", "status", "preferred_role", "minimum_shift_hours", "maximum_hours", "split_shifts_allowed"],
		order_by="applied_on asc",
		limit_page_length=500,
	)
	for row in applications:
		row.employee_name = frappe.db.get_value("Employee", row.employee, "employee_name")
		row.availability_windows = frappe.get_all(
			"Roster Availability Window",
			filters={"parent": row.name, "parenttype": "Roster Application"},
			fields=["work_date", "available_from", "available_until", "preference", "preferred_role"],
			order_by="work_date, available_from",
		)
	selections = frappe.get_all(
		"Roster Selection",
		filters={"roster": roster, "docstatus": ["<", 2], "status": ["!=", "Declined"]},
		fields=["name", "employee", "coverage_requirement_idx", "work_date", "selected_from", "selected_until", "assigned_role", "hourly_rate", "docstatus", "status", "employee_confirmation_status"],
		order_by="work_date, selected_from",
		limit_page_length=500,
	)
	return {"roster": doc.as_dict(), "coverage": build_coverage_grid(roster), "applications": applications, "selections": selections}


@frappe.whitelist()
def recommend(roster: str, requirement_idx: int):
	ensure_roles("Roster Manager", "HR Manager", "Malaysia HR Manager", "System Manager")
	frappe.get_doc("Casual Roster", roster).check_permission("read")
	return recommend_for_requirement(roster, int(requirement_idx))


@frappe.whitelist(methods=["POST"])
def respond_to_selection(selection: str, accept: int):
	employee = get_current_employee()
	doc = frappe.get_doc("Roster Selection", selection)
	if doc.employee != employee:
		frappe.throw(_("You can only respond to your own roster selection."), frappe.PermissionError)
	if doc.docstatus != 0 or doc.employee_confirmation_status != "Pending":
		frappe.throw(_("This selection is no longer awaiting confirmation."))
	roster_status = frappe.db.get_value("Casual Roster", doc.roster, "status")
	if roster_status in {"Published", "In Progress", "Completed", "Payroll Ready", "Closed"}:
		frappe.throw(_("This roster has already been published."))
	try:
		accepted = boolean_flag(accept, "Accept Selection")
	except ValueError as exc:
		frappe.throw(_(str(exc)))
	if accepted:
		doc.employee_confirmation_status = "Accepted"
		doc.confirmed_on = now_datetime()
		doc.save(ignore_permissions=True)
		return {"name": doc.name, "status": "Accepted"}
	doc.employee_confirmation_status = "Declined"
	doc.status = "Declined"
	doc.confirmed_on = now_datetime()
	doc.save(ignore_permissions=True)
	other = frappe.db.exists(
		"Roster Selection",
		{
			"application": doc.application,
			"name": ["!=", doc.name],
			"docstatus": ["<", 2],
			"status": ["!=", "Declined"],
		},
	)
	if not other:
		frappe.db.set_value("Roster Application", doc.application, "status", "Applied", update_modified=False)
	return {"name": doc.name, "status": "Declined"}


@frappe.whitelist(methods=["POST"])
def close_applications(roster: str):
	ensure_roles("Roster Manager", "HR Manager", "Malaysia HR Manager", "System Manager")
	doc = frappe.get_doc("Casual Roster", roster)
	return doc.close_applications()


@frappe.whitelist(methods=["POST"])
def publish_roster(roster: str, allow_gaps: int = 0):
	ensure_roles("Roster Manager", "HR Manager", "Malaysia HR Manager", "System Manager")
	doc = frappe.get_doc("Casual Roster", roster)
	return doc.publish_roster(int(allow_gaps or 0))


@frappe.whitelist(methods=["POST"])
def select_employee(
	application: str,
	coverage_requirement_idx: int,
	selected_from: str | None = None,
	selected_until: str | None = None,
	hourly_rate: float | None = None,
	outside_availability_override: int = 0,
	override_reason: str | None = None,
):
	ensure_roles("Roster Manager", "HR Manager", "Malaysia HR Manager", "System Manager")
	application_doc = frappe.get_doc("Roster Application", application)
	roster = frappe.get_doc("Casual Roster", application_doc.roster)
	roster.check_permission("write")
	idx = int(coverage_requirement_idx)
	requirement = next((row for row in roster.coverage_requirements if row.idx == idx), None)
	if not requirement:
		frappe.throw(_("Coverage requirement row {0} does not exist.").format(idx))
	agreement = get_work_agreement(application_doc.employee, requirement.work_date, required=True)
	existing = frappe.db.get_value(
		"Roster Selection",
		{
			"application": application_doc.name,
			"coverage_requirement_idx": idx,
			"selected_from": selected_from or requirement.start_time,
			"selected_until": selected_until or requirement.end_time,
			"docstatus": ["<", 2],
			"status": ["!=", "Declined"],
		},
		["name", "shift_assignment", "shift_work_record"],
		as_dict=True,
	)
	if existing:
		return {
			"name": existing.name,
			"shift_assignment": existing.shift_assignment,
			"shift_work_record": existing.shift_work_record,
			"duplicate_suppressed": True,
		}
	selection = frappe.new_doc("Roster Selection")
	selection.roster = roster.name
	selection.application = application_doc.name
	selection.employee = application_doc.employee
	selection.company = roster.company
	selection.coverage_requirement_idx = idx
	selection.work_date = requirement.work_date
	selection.selected_from = selected_from or requirement.start_time
	selection.selected_until = selected_until or requirement.end_time
	selection.assigned_role = requirement.role
	selection.hourly_rate = hourly_rate or requirement.hourly_rate or agreement.get("base_hourly_rate") or 0
	selection.shift_location = requirement.shift_location or roster.default_shift_location
	selection.cost_center = requirement.cost_center
	selection.project = requirement.project or roster.project
	try:
		selection.outside_availability_override = boolean_flag(
			outside_availability_override,
			"Outside Availability Override",
		)
	except ValueError as exc:
		frappe.throw(_(str(exc)))
	selection.override_reason = override_reason
	selection.insert()
	return {
		"name": selection.name,
		"shift_assignment": selection.shift_assignment,
		"shift_work_record": selection.shift_work_record,
	}
