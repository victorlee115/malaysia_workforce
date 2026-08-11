from __future__ import annotations

from datetime import timedelta

import frappe
from frappe.utils import getdate

from malaysia_workforce.attendance.events import reconcile_work_record
from malaysia_workforce.compliance.exceptions import create_assigned_exception


def reconcile_recent_work_records():
	for name in frappe.get_all(
		"Shift Work Record",
		filters={
			"docstatus": 0,
			"work_date": ["between", [getdate() - timedelta(days=2), getdate() + timedelta(days=1)]],
			"status": ["in", ["Pending Attendance", "Employee Correction Required"]],
		},
		pluck="name",
		limit=1000,
	):
		try:
			reconcile_work_record(name)
		except Exception as exc:
			frappe.log_error(title=f"Attendance reconciliation failed: {name}", message=frappe.get_traceback())
			try:
				create_assigned_exception(
					code="ATTENDANCE-RECONCILIATION",
					description=f"Resolve attendance reconciliation failure for {name}: {exc}",
					reference_type="Shift Work Record",
					reference_name=name,
					due_date=getdate(),
				)
			except Exception:
				frappe.log_error(title=f"Attendance exception assignment failed: {name}", message=frappe.get_traceback())
