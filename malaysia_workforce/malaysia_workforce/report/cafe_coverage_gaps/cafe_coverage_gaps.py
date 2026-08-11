from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.company:
		frappe.throw(_("Company is required."))
	if not frappe.has_permission("Cafe Staffing Plan", "read"):
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	columns = [
		{"label": _("Staffing Plan"), "fieldname": "plan", "fieldtype": "Link", "options": "Cafe Staffing Plan", "width": 170},
		{"label": _("Date"), "fieldname": "work_date", "fieldtype": "Date", "width": 100},
		{"label": _("Starts"), "fieldname": "start_time", "fieldtype": "Time", "width": 90},
		{"label": _("Ends"), "fieldname": "end_time", "fieldtype": "Time", "width": 90},
		{"label": _("Designation"), "fieldname": "designation", "fieldtype": "Link", "options": "Designation", "width": 140},
		{"label": _("Coverage"), "fieldname": "criticality", "fieldtype": "Data", "width": 90},
		{"label": _("Needed"), "fieldname": "required_headcount", "fieldtype": "Int", "width": 75},
		{"label": _("Recommended"), "fieldname": "allocated_headcount", "fieldtype": "Int", "width": 105},
		{"label": _("Uncovered Minutes"), "fieldname": "uncovered_minutes", "fieldtype": "Int", "width": 135},
	]
	plan_filters = {"company": filters.company, "workflow_state": ["in", ["Proposed", "Approved"]]}
	if filters.from_date:
		plan_filters["cycle_end"] = [">=", getdate(filters.from_date)]
	if filters.to_date:
		plan_filters["cycle_start"] = ["<=", getdate(filters.to_date)]
	plans = frappe.get_all("Cafe Staffing Plan", filters=plan_filters, pluck="name", limit=10000)
	data = []
	for name in plans:
		plan = frappe.get_doc("Cafe Staffing Plan", name)
		if not plan.has_permission("read"):
			continue
		for row in plan.requirements:
			if not int(row.uncovered_minutes or 0):
				continue
			if filters.critical_only and row.criticality != "Critical":
				continue
			data.append(
				{
					"plan": plan.name,
					"work_date": row.work_date,
					"start_time": row.start_time,
					"end_time": row.end_time,
					"designation": row.designation,
					"criticality": row.criticality,
					"required_headcount": row.required_headcount,
					"allocated_headcount": row.allocated_headcount,
					"uncovered_minutes": row.uncovered_minutes,
				}
			)
	return columns, sorted(data, key=lambda row: (str(row["work_date"]), str(row["start_time"]), row["plan"]))
