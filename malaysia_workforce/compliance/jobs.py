from __future__ import annotations

import frappe
from frappe.utils import add_days, getdate, today

from malaysia_workforce.compliance.exceptions import create_assigned_exception


def _record_failure(code: str, reference_type: str, reference_name: str, exc: Exception) -> None:
	frappe.log_error(title=f"Malaysia Workforce {code}: {reference_name}", message=frappe.get_traceback())
	try:
		create_assigned_exception(
			code=code,
			description=f"Permanent scheduled-job failure for {reference_type} {reference_name}: {exc}",
			reference_type=reference_type,
			reference_name=reference_name,
			due_date=today(),
		)
	except Exception:
		frappe.log_error(title=f"Malaysia Workforce exception assignment failed: {reference_name}", message=frappe.get_traceback())


def refresh_obligations():
	"""Create missing CP22 work items for recent new hires.

	Cessation/departure forms require facts not reliably inferable from Employee alone,
	so those remain event-driven through the Malaysia Employee Notification action.
	"""
	cutoff = add_days(today(), -30)
	for employee in frappe.get_all("Employee", filters={"status": "Active", "date_of_joining": [">=", cutoff]}, fields=["name", "company", "date_of_joining"], limit=5000):
		try:
			if frappe.db.exists("Malaysia Employee Notification", {"employee": employee.name, "form_type": "CP22", "trigger_date": employee.date_of_joining}):
				continue
			doc = frappe.new_doc("Malaysia Employee Notification")
			doc.employee = employee.name
			doc.company = employee.company
			doc.form_type = "CP22"
			doc.event_type = "Commencement"
			doc.trigger_date = employee.date_of_joining
			doc.due_date = add_days(employee.date_of_joining, 30)
			doc.reason = "Automatically created from Employee Date of Joining"
			doc.insert(ignore_permissions=True)
		except Exception as exc:
			_record_failure("CP22-REFRESH", "Employee", employee.name, exc)


def flag_expired_overrides():
	cutoff = add_days(today(), -365)
	for row in frappe.get_all("Statutory Coverage Profile", filters={"last_reviewed_on": ["<", cutoff]}, fields=["name", "employee"]):
		try:
			create_assigned_exception(
				code=f"STATUTORY-COVERAGE-ANNUAL-REVIEW-{getdate(today()).year}",
				description=f"Review effective statutory coverage and evidence for {row.employee}.",
				reference_type="Statutory Coverage Profile",
				reference_name=row.name,
				due_date=today(),
			)
		except Exception as exc:
			_record_failure("STATUTORY-COVERAGE-REVIEW", "Statutory Coverage Profile", row.name, exc)


def refresh_control_deadlines():
	"""Assign rule-review, HRD headcount, levy and incident deadline controls."""
	settings = frappe.get_cached_doc("Malaysia Workforce Settings")
	if settings.rules_reviewed_through and getdate(settings.rules_reviewed_through) <= getdate(add_days(today(), 30)):
		try:
			create_assigned_exception(
				code=f"RULE-PACK-REVIEW-{settings.rules_reviewed_through}",
				description=f"Review Malaysian statutory sources before the rule pack expires on {settings.rules_reviewed_through}.",
				reference_type="Malaysia Workforce Settings",
				reference_name="Malaysia Workforce Settings",
				due_date=settings.rules_reviewed_through,
			)
		except Exception as exc:
			_record_failure("RULE-PACK-REVIEW", "Malaysia Workforce Settings", "Malaysia Workforce Settings", exc)
	for company in frappe.get_all("Company", filters={"custom_enable_malaysia_payroll": 1}, pluck="name"):
		try:
			headcount = frappe.db.count("Employee", {"company": company, "status": "Active"})
			registered, registration_number = frappe.db.get_value(
				"Company", company, ["custom_hrd_corp_registered", "custom_hrd_corp_registration_number"]
			)
			if headcount >= 10 and (not registered or not registration_number):
				create_assigned_exception(
					code="HRDCORP-REGISTRATION-THRESHOLD",
					description=f"{company} has {headcount} active employees. Complete and evidence HRD Corp registration.",
					reference_type="Company",
					reference_name=company,
					due_date=today(),
				)
			elif headcount in {8, 9}:
				create_assigned_exception(
					code=f"HRDCORP-HEADCOUNT-WARNING-{headcount}",
					description=f"{company} has {headcount} active employees and is approaching the configured HRD Corp threshold.",
					reference_type="Company",
					reference_name=company,
					due_date=add_days(today(), 7),
				)
		except Exception as exc:
			_record_failure("CONTROL-DEADLINE", "Company", company, exc)

	for issue in frappe.get_all(
		"Issue",
		filters={
			"custom_malaysia_workplace_incident": 1,
			"status": ["not in", ["Closed", "Resolved"]],
			"custom_perkeso_escalation_due": ["<=", add_days(today(), 1)],
		},
		fields=["name", "custom_perkeso_escalation_due"],
		limit=10000,
	):
		try:
			create_assigned_exception(
				code="PERKESO-INCIDENT-48H",
				description=f"PERKESO incident action for {issue.name} is due by {issue.custom_perkeso_escalation_due}.",
				reference_type="Issue",
				reference_name=issue.name,
				due_date=getdate(issue.custom_perkeso_escalation_due),
			)
		except Exception as exc:
			_record_failure("PERKESO-INCIDENT-48H", "Issue", issue.name, exc)
