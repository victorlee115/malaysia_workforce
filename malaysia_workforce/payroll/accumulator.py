from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import get_first_day

from malaysia_workforce.statutory.snapshot import parse_statutory_snapshot


def update_accumulator_from_salary_slip(doc) -> str | None:
	if not doc.custom_malaysia_statutory_snapshot:
		return None
	try:
		snapshot = parse_statutory_snapshot(doc.custom_malaysia_statutory_snapshot)
	except ValueError as exc:
		frappe.throw(
			_("Salary Slip {0} has an invalid Malaysia statutory snapshot: {1}").format(doc.name, exc)
		)
	month = get_first_day(doc.end_date)
	name = frappe.db.get_value(
		"Monthly Statutory Accumulator",
		{"employee": doc.employee, "company": doc.company, "contribution_month": month, "status": ["in", ["Open", "Frozen"]]},
		"name",
	)
	acc = frappe.get_doc("Monthly Statutory Accumulator", name) if name else frappe.new_doc("Monthly Statutory Accumulator")
	if not name:
		acc.employee = doc.employee
		acc.company = doc.company
		acc.contribution_month = month
		acc.status = "Open"
	# Idempotent replacement by source reference.
	acc.set("items", [row for row in acc.items if not (row.source_doctype == "Salary Slip" and row.source_name == doc.name)])
	bases = snapshot.get("current_wage_bases", {})
	acc.append(
		"items",
		{
			"source_doctype": "Salary Slip",
			"source_name": doc.name,
			"pay_date": doc.posting_date,
			"gross": bases.get("gross", 0),
			"epf_wages": bases.get("epf", 0),
			"socso_wages": bases.get("socso", 0),
			"eis_wages": bases.get("eis", 0),
			"pcb_regular": bases.get("pcb_regular", 0),
			"pcb_additional": bases.get("pcb_additional", 0),
		},
	)
	acc.set("statutory_results", [])
	for result in snapshot.get("month_total_results", []):
		acc.append("statutory_results", result)
	acc.calculation_snapshot = json.dumps(snapshot, sort_keys=True)
	acc.save(ignore_permissions=True)
	return acc.name


def remove_salary_slip_from_accumulator(doc) -> None:
	month = get_first_day(doc.end_date)
	name = frappe.db.get_value(
		"Monthly Statutory Accumulator",
		{"employee": doc.employee, "company": doc.company, "contribution_month": month, "status": ["in", ["Open", "Frozen"]]},
		"name",
	)
	if not name:
		return
	acc = frappe.get_doc("Monthly Statutory Accumulator", name)
	acc.set("items", [row for row in acc.items if not (row.source_doctype == "Salary Slip" and row.source_name == doc.name)])
	if acc.items:
		acc.save(ignore_permissions=True)
	else:
		frappe.delete_doc("Monthly Statutory Accumulator", acc.name, ignore_permissions=True)
