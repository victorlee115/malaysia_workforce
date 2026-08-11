from __future__ import annotations

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import get_datetime, getdate, now_datetime

from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee

from malaysia_workforce.data_access import get_work_agreement


def _is_public_holiday(employee: str, work_date) -> bool:
	holiday_list = get_holiday_list_for_employee(employee, raise_exception=False)
	if not holiday_list:
		return False
	return bool(
		frappe.db.exists(
			"Holiday",
			{"parent": holiday_list, "holiday_date": getdate(work_date), "weekly_off": 0},
		)
	)


def _is_rest_day(employee: str, work_date) -> bool:
	agreement = get_work_agreement(employee, work_date)
	if not agreement or not agreement.get("weekly_rest_day"):
		return False
	return getdate(work_date).strftime("%A") == agreement.get("weekly_rest_day")


def on_shift_assignment_submit(doc, method=None):
	if not getattr(doc, "custom_malaysia_staffing_plan", None):
		return
	existing = frappe.db.get_value("Shift Work Record", {"shift_assignment": doc.name, "docstatus": ["<", 2]}, "name")
	if existing:
		doc.db_set("custom_shift_work_record", existing, update_modified=False)
		return
	shift = frappe.db.get_value("Shift Type", doc.shift_type, ["start_time", "end_time"], as_dict=True)
	if not shift:
		frappe.throw(_("Shift Assignment requires a valid Shift Type."))
	from malaysia_workforce.staffing.intervals import coerce_time
	from datetime import datetime

	start = datetime.combine(getdate(doc.start_date), coerce_time(shift.start_time))
	end = datetime.combine(getdate(doc.start_date), coerce_time(shift.end_time))
	if end <= start:
		end += timedelta(days=1)

	record = frappe.new_doc("Shift Work Record")
	record.employee = doc.employee
	record.company = doc.company
	record.staffing_plan = doc.custom_malaysia_staffing_plan
	record.staffing_recommendation_key = doc.custom_malaysia_staffing_recommendation_key
	record.shift_assignment = doc.name
	record.work_date = getdate(doc.start_date)
	record.scheduled_start = start
	record.scheduled_end = end
	record.rate_snapshot = doc.custom_malaysia_rate_snapshot
	record.is_public_holiday = _is_public_holiday(doc.employee, record.work_date)
	record.is_rest_day = _is_rest_day(doc.employee, record.work_date)
	record.status = "Pending Attendance"
	record.insert(ignore_permissions=True)
	doc.db_set("custom_shift_work_record", record.name, update_modified=False)


def on_shift_assignment_cancel(doc, method=None):
	name = getattr(doc, "custom_shift_work_record", None) or frappe.db.get_value(
		"Shift Work Record", {"shift_assignment": doc.name, "docstatus": ["<", 2]}, "name"
	)
	if not name:
		return
	record = frappe.get_doc("Shift Work Record", name)
	if record.status == "Payroll Generated" or record.additional_salary_references:
		frappe.throw(_("The linked work record has generated payroll and cannot be cancelled directly."))
	if record.docstatus == 1:
		record.cancel()
	else:
		record.status = "Cancelled"
		record.save(ignore_permissions=True)


def on_employee_checkin(doc, method=None):
	if not doc.employee:
		return
	frappe.enqueue(
		"malaysia_workforce.attendance.events.reconcile_employee_work_records",
		queue="short",
		employee=doc.employee,
		reference_time=doc.time,
		enqueue_after_commit=True,
		job_id=f"mw-reconcile-{doc.employee}-{get_datetime(doc.time).strftime('%Y%m%d%H%M')}",
		deduplicate=True,
	)


def protect_employee_checkin_evidence(doc, method=None):
	"""Keep signed kiosk events and correction proposals immutable through normal saves."""
	before = doc.get_doc_before_save()
	if not before:
		return
	if not before.custom_kiosk_event_id and not before.custom_malaysia_correction_pair_id:
		return
	protected = (
		"employee",
		"log_type",
		"time",
		"device_id",
		"skip_auto_attendance",
		"custom_shift_work_record",
		"custom_kiosk_event_id",
		"custom_kiosk_id",
		"custom_device_timestamp",
		"custom_server_received_timestamp",
		"custom_kiosk_clock_drift_seconds",
		"custom_kiosk_event_hash",
		"custom_malaysia_correction_pair_id",
		"custom_malaysia_correction_status",
		"custom_malaysia_correction_explanation",
		"custom_malaysia_correction_requested_by",
		"custom_malaysia_correction_requested_on",
		"custom_malaysia_correction_reviewed_by",
		"custom_malaysia_correction_reviewed_on",
		"custom_malaysia_correction_evidence",
	)
	if any(str(before.get(fieldname) or "") != str(doc.get(fieldname) or "") for fieldname in protected):
		frappe.throw(_("Protected kiosk or attendance-correction evidence cannot be edited directly."))


def prevent_employee_checkin_evidence_deletion(doc, method=None):
	if doc.custom_kiosk_event_id or doc.custom_malaysia_correction_pair_id:
		frappe.throw(
			_("Protected kiosk and correction check-ins cannot be deleted. Use the evidenced correction workflow.")
		)


def _checkin_window(record):
	before = int(frappe.db.get_single_value("Malaysia Workforce Settings", "checkin_grace_before_minutes") or 120)
	after = int(frappe.db.get_single_value("Malaysia Workforce Settings", "checkout_grace_after_minutes") or 180)
	return get_datetime(record.scheduled_start) - timedelta(minutes=before), get_datetime(record.scheduled_end) + timedelta(minutes=after)


def reconcile_employee_work_records(employee: str, reference_time=None):
	filters = {"employee": employee, "docstatus": 0, "status": ["in", ["Pending Attendance", "Employee Correction Required", "Manager Review"]]}
	if reference_time:
		day = getdate(reference_time)
		filters["work_date"] = ["between", [day - timedelta(days=1), day + timedelta(days=1)]]
	for name in frappe.get_all("Shift Work Record", filters=filters, pluck="name", limit=100):
		reconcile_work_record(name)


def reconcile_work_record(name: str):
	record = frappe.get_doc("Shift Work Record", name)
	if record.docstatus != 0 or record.status in {"Cancelled", "Payroll Generated"}:
		return
	if record.status == "Manager Review" and record.actual_check_in and record.actual_check_out:
		# Preserve an employee correction or a completed exception until a manager decides it.
		return
	window_start, window_end = _checkin_window(record)
	checkins = frappe.get_all(
		"Employee Checkin",
		filters={"employee": record.employee, "time": ["between", [window_start, window_end]], "skip_auto_attendance": 0},
		fields=["name", "time", "log_type", "custom_shift_work_record", "custom_malaysia_correction_status"],
		order_by="time asc",
		limit=100,
	)
	checkins = [
		row
		for row in checkins
		if not row.custom_shift_work_record or row.custom_shift_work_record == record.name
	]
	approved_corrections = [
		row for row in checkins if row.custom_malaysia_correction_status == "Approved"
	]
	if approved_corrections:
		checkins = approved_corrections
	ins = [row for row in checkins if row.log_type == "IN"]
	outs = [row for row in checkins if row.log_type == "OUT"]
	if ins and outs:
		check_in = ins[0]
		valid_outs = [row for row in outs if get_datetime(row.time) > get_datetime(check_in.time)]
		check_out = valid_outs[-1] if valid_outs else None
	elif len(checkins) >= 2:
		check_in, check_out = checkins[0], checkins[-1]
	else:
		check_in = checkins[0] if checkins else None
		check_out = None

	if check_in:
		record.actual_check_in = check_in.time
		frappe.db.set_value(
			"Employee Checkin",
			check_in.name,
			{"custom_shift_work_record": record.name},
			update_modified=False,
		)
	if check_out:
		record.actual_check_out = check_out.time
		frappe.db.set_value(
			"Employee Checkin",
			check_out.name,
			{"custom_shift_work_record": record.name},
			update_modified=False,
		)

	if record.actual_check_in and record.actual_check_out:
		tolerance = int(
			frappe.db.get_single_value("Malaysia Workforce Settings", "auto_approve_time_tolerance_minutes") or 15
		)
		start_delta = abs((get_datetime(record.actual_check_in) - get_datetime(record.scheduled_start)).total_seconds()) / 60
		end_delta = abs((get_datetime(record.actual_check_out) - get_datetime(record.scheduled_end)).total_seconds()) / 60
		if start_delta <= tolerance and end_delta <= tolerance:
			record.status = "Automatically Verified"
			record.attendance_exception = ""
		else:
			record.status = "Manager Review"
			record.attendance_exception = (
				f"Actual times differ from schedule by {start_delta:.0f} minute(s) at start and "
				f"{end_delta:.0f} minute(s) at end."
			)
		record.save(ignore_permissions=True)
		if record.status == "Automatically Verified" and frappe.db.get_single_value(
			"Malaysia Workforce Settings", "auto_submit_verified_work_records"
		):
			record.submit()
	elif now_datetime() > window_end:
		record.status = "Employee Correction Required"
		record.attendance_exception = "Missing check-in or check-out."
		record.save(ignore_permissions=True)
	else:
		record.save(ignore_permissions=True)
