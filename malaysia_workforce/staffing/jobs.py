from __future__ import annotations

import frappe
from frappe.utils import add_to_date, get_datetime, getdate, now_datetime

from malaysia_workforce.compliance.exceptions import create_assigned_exception
from malaysia_workforce.data_access import get_work_agreement


def _eligible_employees(plan):
	filters = {"company": plan.company, "status": "Active", "user_id": ["is", "set"]}
	if plan.branch:
		filters["branch"] = plan.branch
	for employee in frappe.get_all(
		"Employee", filters=filters, fields=["name", "employee_name", "user_id"], limit=100000
	):
		agreement = get_work_agreement(employee.name, plan.cycle_start)
		if agreement and agreement.work_arrangement in {"Casual", "Part Time"}:
			yield employee


def send_availability_reminders():
	"""Send native Notification Log reminders at 48 and 24 hours before cutoff."""
	now = now_datetime()
	cutoff = add_to_date(now, hours=48)
	for row in frappe.get_all(
		"Cafe Staffing Plan",
		filters={
			"workflow_state": "Collecting Availability",
			"availability_closes": ["between", [now, cutoff]],
		},
		fields=["name", "plan_title", "company", "branch", "cycle_start", "availability_closes"],
		limit=1000,
	):
		remaining_hours = max(int((get_datetime(row.availability_closes) - now).total_seconds() // 3600), 0)
		bucket = 24 if remaining_hours <= 24 else 48
		for employee in _eligible_employees(row):
			if frappe.db.exists(
				"Casual Availability",
				{
					"employee": employee.name,
					"company": row.company,
					"cycle_start": row.cycle_start,
					"status": "Submitted",
				},
			):
				continue
			subject = f"Availability closes in {bucket} hours: {row.plan_title}"
			if frappe.db.exists(
				"Notification Log",
				{
					"for_user": employee.user_id,
					"subject": subject,
					"document_type": "Cafe Staffing Plan",
					"document_name": row.name,
				},
			):
				continue
			frappe.get_doc(
				{
					"doctype": "Notification Log",
					"subject": subject,
					"email_content": "Submit your availability from the My Availability link. Availability is not a confirmed shift.",
					"for_user": employee.user_id,
					"type": "Alert",
					"document_type": "Cafe Staffing Plan",
					"document_name": row.name,
					"from_user": "Administrator",
				}
			).insert(ignore_permissions=True)


def close_availability_windows():
	for row in frappe.get_all(
		"Cafe Staffing Plan",
		filters={"workflow_state": "Collecting Availability", "availability_closes": ["<=", now_datetime()]},
		fields=["name", "plan_title", "company", "branch", "cycle_start", "manager", "approval_due"],
		limit=1000,
	):
		for employee in _eligible_employees(row):
			if frappe.db.exists(
				"Casual Availability",
				{
					"employee": employee.name,
					"company": row.company,
					"cycle_start": row.cycle_start,
					"status": "Submitted",
				},
			):
				continue
			create_assigned_exception(
				code=f"MISSING-AVAILABILITY-{row.name}-{employee.name}",
				description=f"Record that {employee.employee_name} did not submit availability for {row.plan_title}; they will be treated as unavailable.",
				reference_type="Cafe Staffing Plan",
				reference_name=row.name,
				due_date=getdate(row.approval_due),
				allocated_to=row.manager,
			)
		create_assigned_exception(
			code=f"STAFFING-READY-{row.name}",
			description=f"Availability has closed for {row.plan_title}. Review requirements and generate the proposal.",
			reference_type="Cafe Staffing Plan",
			reference_name=row.name,
			due_date=getdate(row.approval_due),
			allocated_to=row.manager,
		)


def flag_staffing_deadlines():
	for row in frappe.get_all(
		"Cafe Staffing Plan",
		filters={
			"workflow_state": ["in", ["Collecting Availability", "Proposed"]],
			"approval_due": ["<=", now_datetime()],
		},
		fields=["name", "plan_title", "manager", "cycle_start", "unresolved_exception_count"],
		limit=1000,
	):
		create_assigned_exception(
			code=f"STAFFING-OVERDUE-{row.name}",
			description=f"Publish or resolve the overdue staffing plan {row.plan_title} before {row.cycle_start}.",
			reference_type="Cafe Staffing Plan",
			reference_name=row.name,
			due_date=getdate(row.cycle_start),
			allocated_to=row.manager,
		)


def flag_stale_staffing_proposals():
	from malaysia_workforce.staffing.services import current_source

	for name in frappe.get_all(
		"Cafe Staffing Plan",
		filters={"workflow_state": "Proposed", "docstatus": 0},
		pluck="name",
		limit=1000,
	):
		try:
			plan = frappe.get_doc("Cafe Staffing Plan", name)
			current_hash, _, _, _ = current_source(plan)
			if current_hash == plan.source_snapshot_hash:
				continue
			create_assigned_exception(
				code=f"STALE-STAFFING-PROPOSAL-{plan.name}",
				description=f"Availability, leave, eligibility, or shifts changed after proposal {plan.name} was generated. Regenerate it before approval.",
				reference_type=plan.doctype,
				reference_name=plan.name,
				due_date=getdate(plan.approval_due),
				allocated_to=plan.manager,
			)
		except Exception:
			frappe.log_error(title=f"Staffing proposal stale check failed: {name}", message=frappe.get_traceback())


def expire_staffing_priorities():
	for row in frappe.get_all(
		"Employee",
		filters={
			"status": "Active",
			"custom_staffing_priority": ["in", ["Priority", "Preferred"]],
			"custom_staffing_priority_expires_on": ["<", getdate()],
		},
		fields=["name", "employee_name", "custom_staffing_priority", "custom_staffing_priority_reason", "custom_staffing_priority_expires_on"],
		limit=10000,
	):
		create_assigned_exception(
			code=f"EXPIRED-STAFFING-PRIORITY-{row.name}-{row.custom_staffing_priority_expires_on}",
			description=f"{row.employee_name}'s {row.custom_staffing_priority} staffing priority expired on {row.custom_staffing_priority_expires_on} and reverted to Standard. Review the prior reason: {row.custom_staffing_priority_reason}",
			reference_type="Employee",
			reference_name=row.name,
		)
		frappe.db.set_value(
			"Employee",
			row.name,
			{
				"custom_staffing_priority": "Standard",
				"custom_staffing_priority_reason": None,
				"custom_staffing_priority_effective_from": None,
				"custom_staffing_priority_expires_on": None,
				"custom_staffing_priority_reviewed_by": "Administrator",
				"custom_staffing_priority_reviewed_on": now_datetime(),
			},
			update_modified=True,
		)
