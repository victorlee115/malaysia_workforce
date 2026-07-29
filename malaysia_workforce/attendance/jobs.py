from __future__ import annotations

from datetime import timedelta

import frappe
from frappe.utils import getdate

from malaysia_workforce.attendance.events import reconcile_work_record


def reconcile_recent_work_records():
	for name in frappe.get_all(
		"Shift Work Record",
		filters={
			"docstatus": 0,
			"work_date": ["between", [getdate() - timedelta(days=2), getdate() + timedelta(days=1)]],
			"status": ["in", ["Pending Attendance", "Employee Correction Required"]],
		},
		pluck="name",
		limit_page_length=1000,
	):
		reconcile_work_record(name)
