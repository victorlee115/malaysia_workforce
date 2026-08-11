from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_to_date, get_datetime

from malaysia_workforce.compliance.exceptions import create_assigned_exception
from malaysia_workforce.utils import ensure_roles


@frappe.whitelist(methods=["POST"])
def record_workplace_incident(
	company: str,
	subject: str,
	description: str,
	occurred_on: str,
	employee: str | None = None,
	dosh_reporting_required: int = 0,
) -> dict:
	"""Record an incident in standard ERPNext Issue and assign statutory escalations."""
	ensure_roles("HR Manager", "Malaysia HR Manager", "System Manager")
	if not subject or not description:
		frappe.throw(_("Incident subject and description are required."))
	company_doc = frappe.get_doc("Company", company)
	company_doc.check_permission("read")
	if employee and frappe.db.get_value("Employee", employee, "company") != company:
		frappe.throw(_("Affected Employee belongs to another Company."))
	occurred = get_datetime(occurred_on)
	due = add_to_date(occurred, hours=48)
	issue = frappe.get_doc(
		{
			"doctype": "Issue",
			"subject": subject,
			"description": description,
			"priority": "High",
			"status": "Open",
			"custom_malaysia_workplace_incident": 1,
			"custom_incident_company": company,
			"custom_incident_employee": employee,
			"custom_incident_occurred_on": occurred,
			"custom_perkeso_escalation_due": due,
			"custom_dosh_reporting_required": int(dosh_reporting_required or 0),
		}
	)
	issue.insert(ignore_permissions=True)
	todos = [
		create_assigned_exception(
			code="PERKESO-INCIDENT-48H",
			description=f"Assess and record the required PERKESO incident action for {issue.name} within 48 hours.",
			reference_type="Issue",
			reference_name=issue.name,
			due_date=due,
		)
	]
	if int(dosh_reporting_required or 0):
		todos.append(
			create_assigned_exception(
				code="DOSH-INCIDENT-REPORT",
				description=f"Prepare the required DOSH notification and retain evidence for {issue.name}.",
				reference_type="Issue",
				reference_name=issue.name,
				due_date=due,
			)
		)
	return {"issue": issue.name, "assigned_todos": todos, "perkeso_escalation_due": due}


def annual_incident_register(company: str, year: int) -> list[dict]:
	"""Return source rows for the annual register; standard report/export tools own presentation."""
	frappe.get_doc("Company", company).check_permission("read")
	return frappe.get_all(
		"Issue",
		filters={
			"custom_incident_company": company,
			"custom_malaysia_workplace_incident": 1,
			"custom_incident_occurred_on": ["between", [f"{int(year)}-01-01", f"{int(year)}-12-31 23:59:59"]],
		},
		fields=[
			"name",
			"subject",
			"status",
			"custom_incident_employee",
			"custom_incident_occurred_on",
			"custom_perkeso_escalation_due",
			"custom_dosh_reporting_required",
			"custom_incident_report_evidence",
		],
		order_by="custom_incident_occurred_on asc",
		limit=10000,
	)
