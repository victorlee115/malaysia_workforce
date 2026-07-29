from __future__ import annotations

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import cstr, get_datetime, now_datetime

from malaysia_workforce.attendance.events import reconcile_work_record
from malaysia_workforce.utils import ensure_roles, get_current_employee


def _current_work_record(employee: str):
	now = now_datetime()
	candidates = frappe.get_all(
		"Shift Work Record",
		filters={
			"employee": employee,
			"docstatus": 0,
			"status": ["not in", ["Cancelled", "Payroll Generated"]],
			"scheduled_start": ["<=", now + timedelta(hours=4)],
			"scheduled_end": [">=", now - timedelta(hours=4)],
		},
		fields=["name", "scheduled_start", "scheduled_end", "roster_selection", "shift_assignment"],
		order_by="scheduled_start asc",
		limit_page_length=20,
	)
	if not candidates:
		return None
	return min(candidates, key=lambda row: abs((get_datetime(row.scheduled_start) - now).total_seconds()))


def _coordinates(latitude, longitude) -> tuple[float | None, float | None]:
	if latitude in (None, "") and longitude in (None, ""):
		return None, None
	if latitude in (None, "") or longitude in (None, ""):
		frappe.throw(_("Both latitude and longitude are required."))
	try:
		lat, lon = float(latitude), float(longitude)
	except (TypeError, ValueError):
		frappe.throw(_("Latitude and longitude must be valid numbers."))
	if not -90 <= lat <= 90 or not -180 <= lon <= 180:
		frappe.throw(_("Latitude or longitude is outside the valid range."))
	return lat, lon


def _last_checkin_for_record(employee: str, record):
	start = get_datetime(record.scheduled_start) - timedelta(hours=4)
	end = now_datetime() + timedelta(minutes=1)
	rows = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": employee,
			"time": ["between", [start, end]],
			"skip_auto_attendance": 0,
		},
		fields=["name", "time", "log_type", "shift", "custom_shift_work_record", "custom_roster_selection"],
		order_by="time desc",
		limit_page_length=50,
	)
	for row in rows:
		if row.custom_shift_work_record == record.name or (
			record.roster_selection and row.custom_roster_selection == record.roster_selection
		):
			return row
	shift_type = frappe.db.get_value("Shift Assignment", record.shift_assignment, "shift_type")
	return next((row for row in rows if not row.custom_shift_work_record and row.shift == shift_type), None)


@frappe.whitelist(methods=["POST"])
def clock(
	log_type: str,
	latitude: float | None = None,
	longitude: float | None = None,
	device_id: str | None = None,
):
	employee = get_current_employee()
	log_type = (log_type or "").upper()
	if log_type not in {"IN", "OUT"}:
		frappe.throw(_("Log type must be IN or OUT."))
	record = _current_work_record(employee)
	if not record:
		frappe.throw(_("No confirmed roster shift was found near the current time."))

	lat, lon = _coordinates(latitude, longitude)
	settings = frappe.get_cached_doc("Malaysia Workforce Settings")
	if settings.require_geolocation_for_mobile_checkin and (lat is None or lon is None):
		frappe.throw(
			_("Location permission is required for mobile clocking. Enable location access and try again.")
		)

	last = _last_checkin_for_record(employee, record)
	if last and last.log_type == log_type:
		if (now_datetime() - get_datetime(last.time)).total_seconds() < 60:
			return {"name": last.name, "time": last.time, "duplicate_suppressed": True}
		if settings.prevent_consecutive_same_checkin_type:
			frappe.throw(
				_("Your most recent attendance record is already {0}. Record {1} next.").format(
					log_type, "OUT" if log_type == "IN" else "IN"
				)
			)
	if log_type == "OUT" and not last:
		frappe.throw(_("Clock in before recording a clock out."))

	checkin = frappe.new_doc("Employee Checkin")
	checkin.employee = employee
	checkin.log_type = log_type
	checkin.time = now_datetime()
	checkin.device_id = cstr(device_id or "Malaysia Workforce Portal")[:140]
	checkin.latitude = lat
	checkin.longitude = lon
	checkin.custom_checkin_method = "Mobile"
	checkin.custom_shift_work_record = record.name
	checkin.custom_roster_selection = record.roster_selection
	checkin.insert(ignore_permissions=True)
	reconcile_work_record(record.name)
	return {"name": checkin.name, "work_record": record.name, "time": checkin.time}


@frappe.whitelist(methods=["POST"])
def submit_time_correction(work_record: str, actual_check_in: str, actual_check_out: str, explanation: str):
	employee = get_current_employee()
	doc = frappe.get_doc("Shift Work Record", work_record)
	if doc.employee != employee:
		frappe.throw(_("You can only correct your own work record."), frappe.PermissionError)
	if doc.docstatus != 0 or doc.status in {"Payroll Generated", "Cancelled"}:
		frappe.throw(_("This work record can no longer be corrected."))
	if not cstr(explanation).strip():
		frappe.throw(_("Explain why the attendance record needs correction."))
	start, end = get_datetime(actual_check_in), get_datetime(actual_check_out)
	if end <= start:
		frappe.throw(_("Actual Check Out must be after Actual Check In."))
	if (end - start).total_seconds() > 24 * 3600:
		frappe.throw(_("A corrected shift cannot exceed 24 hours."))
	doc.actual_check_in = start
	doc.actual_check_out = end
	doc.attendance_exception = cstr(explanation).strip()[:1000]
	doc.status = "Manager Review"
	doc.save(ignore_permissions=True)
	return {"name": doc.name, "status": doc.status}


@frappe.whitelist(methods=["POST"])
def approve_work_record(work_record: str, unpaid_break_minutes: int = 0, paid_break_minutes: int = 0):
	ensure_roles("Roster Manager", "HR Manager", "Malaysia HR Manager", "Malaysia Payroll User", "System Manager")
	doc = frappe.get_doc("Shift Work Record", work_record)
	doc.check_permission("write")
	if doc.docstatus != 0:
		frappe.throw(_("Only draft work records can be approved."))
	doc.unpaid_break_minutes = int(unpaid_break_minutes or 0)
	doc.paid_break_minutes = int(paid_break_minutes or 0)
	doc.status = "Approved"
	doc.save()
	doc.submit()
	return {"name": doc.name, "status": doc.status, "gross_pay": doc.gross_pay}
