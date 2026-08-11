from __future__ import annotations

import hashlib
import hmac
import re
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import cstr, get_datetime, now_datetime

from malaysia_workforce.attendance.events import reconcile_work_record
from malaysia_workforce.compliance.exceptions import create_assigned_exception
from malaysia_workforce.utils import ensure_private_file, ensure_roles, get_current_employee, select_for_update


EVENT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$")


def _current_work_record(employee: str, at_time=None):
	now = get_datetime(at_time) if at_time else now_datetime()
	candidates = frappe.get_all(
		"Shift Work Record",
		filters={
			"employee": employee,
			"docstatus": 0,
			"status": ["not in", ["Cancelled", "Payroll Generated"]],
			"scheduled_start": ["<=", now + timedelta(hours=4)],
			"scheduled_end": [">=", now - timedelta(hours=4)],
		},
		fields=["name", "scheduled_start", "scheduled_end", "shift_assignment"],
		order_by="scheduled_start asc",
		limit=20,
	)
	if not candidates:
		return None
	return min(candidates, key=lambda row: abs((get_datetime(row.scheduled_start) - now).total_seconds()))


def _kiosk_secret(settings) -> str:
	try:
		return settings.get_password("kiosk_shared_secret", raise_exception=False) or ""
	except TypeError:
		return settings.get_password("kiosk_shared_secret") or ""


def _credential_hash(secret: str, employee: str, credential: str) -> str:
	return hmac.new(secret.encode(), f"{employee}|{credential}".encode(), hashlib.sha256).hexdigest()


def _event_payload(event_id: str, kiosk_id: str, employee: str, log_type: str, device_timestamp: str) -> str:
	return "|".join((event_id, kiosk_id, employee, log_type, device_timestamp))


@frappe.whitelist(methods=["POST"])
def set_kiosk_credential(employee: str, credential: str):
	"""Set/rotate a PIN or QR secret without storing the original credential."""
	ensure_roles("HR Manager", "Malaysia HR Manager", "System Manager")
	if not credential or not 4 <= len(str(credential)) <= 128:
		frappe.throw(_("Kiosk credential must contain 4 to 128 characters."))
	settings = frappe.get_cached_doc("Malaysia Workforce Settings")
	secret = _kiosk_secret(settings)
	if not settings.kiosk_enabled or not secret:
		frappe.throw(_("Enable the kiosk and configure its signing secret first."))
	frappe.get_doc("Employee", employee).check_permission("write")
	frappe.db.set_value(
		"Employee",
		employee,
		"custom_kiosk_credential_hash",
		_credential_hash(secret, employee, str(credential)),
		update_modified=True,
	)
	return {"employee": employee, "credential_rotated": True}


@frappe.whitelist(methods=["POST"])
def kiosk_clock(
	event_id: str,
	kiosk_id: str,
	employee: str,
	credential: str,
	log_type: str,
	device_timestamp: str,
	signature: str,
	offline_queued: int = 0,
):
	"""Create an idempotent standard Employee Checkin from a registered cafe kiosk."""
	ensure_roles("Malaysia Kiosk", "System Manager")
	event_id = cstr(event_id).strip()
	kiosk_id = cstr(kiosk_id).strip()
	employee = cstr(employee).strip()
	log_type = cstr(log_type).upper().strip()
	device_timestamp = cstr(device_timestamp).strip()
	if not EVENT_ID_RE.fullmatch(event_id):
		frappe.throw(_("Event ID must contain 8 to 128 safe identifier characters."))
	if log_type not in {"IN", "OUT"}:
		frappe.throw(_("Log type must be IN or OUT."))

	settings = frappe.get_cached_doc("Malaysia Workforce Settings")
	secret = _kiosk_secret(settings)
	if not settings.kiosk_enabled or not secret or kiosk_id != cstr(settings.kiosk_device_id):
		frappe.throw(_("This kiosk is disabled or not the registered outlet device."), frappe.PermissionError)
	payload = _event_payload(event_id, kiosk_id, employee, log_type, device_timestamp)
	expected_signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
	if not hmac.compare_digest(expected_signature, cstr(signature).lower()):
		frappe.throw(_("Kiosk event signature is invalid."), frappe.PermissionError)

	# Authenticate before disclosing whether an event identifier already exists.
	# A correctly signed offline queue may still retry safely and receive the same result.
	existing = frappe.db.get_value("Employee Checkin", {"custom_kiosk_event_id": event_id}, "name")
	if existing:
		return {"name": existing, "duplicate": True}

	employee_doc = frappe.get_doc("Employee", employee)
	if employee_doc.status != "Active":
		frappe.throw(_("Employee is not active."))
	expected_credential = employee_doc.get("custom_kiosk_credential_hash") or ""
	actual_credential = _credential_hash(secret, employee, cstr(credential))
	if not expected_credential or not hmac.compare_digest(expected_credential, actual_credential):
		frappe.throw(_("Employee kiosk credential is invalid."), frappe.PermissionError)

	device_time = get_datetime(device_timestamp)
	server_time = now_datetime()
	drift = (server_time - device_time).total_seconds()
	max_drift = max(int(settings.kiosk_max_clock_drift_seconds or 300), 0)
	if drift < -max_drift:
		frappe.throw(_("Kiosk timestamp is too far in the future. Synchronize the device clock."))
	clock_warning = abs(drift) > max_drift
	if clock_warning and not int(offline_queued or 0):
		frappe.throw(_("Kiosk clock drift exceeds the configured limit. Synchronize the device or flag an offline replay."))

	record = _current_work_record(employee, device_time)
	if not record:
		frappe.throw(_("No published Shift Assignment was found near the device timestamp."))
	last = _last_checkin_for_record(employee, record)
	if last and last.log_type == log_type and settings.prevent_consecutive_same_checkin_type:
		frappe.throw(_("The most recent kiosk event for this shift is already {0}.").format(log_type))
	if log_type == "OUT" and not last:
		frappe.throw(_("Clock in before recording a clock out."))

	event_hash = hashlib.sha256(payload.encode()).hexdigest()
	checkin = frappe.get_doc(
		{
			"doctype": "Employee Checkin",
			"employee": employee,
			"log_type": log_type,
			"time": device_time,
			"device_id": kiosk_id[:140],
			"custom_checkin_method": "Kiosk",
			"custom_shift_work_record": record.name,
			"custom_kiosk_event_id": event_id,
			"custom_kiosk_id": kiosk_id,
			"custom_device_timestamp": device_time,
			"custom_server_received_timestamp": server_time,
			"custom_kiosk_clock_drift_seconds": drift,
			"custom_kiosk_event_hash": event_hash,
		}
	)
	try:
		checkin.insert(ignore_permissions=True)
	except frappe.DuplicateEntryError:
		existing = frappe.db.get_value("Employee Checkin", {"custom_kiosk_event_id": event_id}, "name")
		if existing:
			return {"name": existing, "duplicate": True}
		raise
	frappe.db.set_single_value("Malaysia Workforce Settings", "kiosk_last_seen_on", server_time)
	reconcile_work_record(record.name)
	return {
		"name": checkin.name,
		"work_record": record.name,
		"time": checkin.time,
		"clock_drift_seconds": drift,
		"clock_warning": clock_warning,
	}


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
		fields=["name", "time", "log_type", "shift", "custom_shift_work_record"],
		order_by="time desc",
		limit=50,
	)
	for row in rows:
		if row.custom_shift_work_record == record.name:
			return row
	shift_type = frappe.db.get_value("Shift Assignment", record.shift_assignment, "shift_type")
	return next((row for row in rows if not row.custom_shift_work_record and row.shift == shift_type), None)


@frappe.whitelist(methods=["POST"])
def submit_time_correction(work_record: str, actual_check_in: str, actual_check_out: str, explanation: str):
	"""Request corrected punches using standard Employee Checkin records."""
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
	if start < get_datetime(doc.scheduled_start) - timedelta(hours=12) or end > get_datetime(
		doc.scheduled_end
	) + timedelta(hours=12):
		frappe.throw(_("Corrected punches must remain within 12 hours of the scheduled shift."))
	pending = frappe.db.get_value(
		"Employee Checkin",
		{
			"custom_shift_work_record": doc.name,
			"custom_malaysia_correction_status": "Pending Review",
		},
		"custom_malaysia_correction_pair_id",
	)
	if pending:
		return {"work_record": doc.name, "correction_pair_id": pending, "status": "Pending Review"}
	pair_id = f"MW-CORR-{frappe.generate_hash(length=20)}"
	requested_on = now_datetime()
	created = []
	for log_type, timestamp in (("IN", start), ("OUT", end)):
		checkin = frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": employee,
				"log_type": log_type,
				"time": timestamp,
				"device_id": "Malaysia Attendance Correction",
				"skip_auto_attendance": 1,
				"custom_checkin_method": "Manual",
				"custom_shift_work_record": doc.name,
				"custom_malaysia_correction_pair_id": pair_id,
				"custom_malaysia_correction_status": "Pending Review",
				"custom_malaysia_correction_explanation": cstr(explanation).strip()[:1000],
				"custom_malaysia_correction_requested_by": frappe.session.user,
				"custom_malaysia_correction_requested_on": requested_on,
			}
		)
		checkin.insert(ignore_permissions=True)
		created.append(checkin.name)
	doc.attendance_exception = cstr(explanation).strip()[:1000]
	doc.status = "Manager Review"
	doc.save(ignore_permissions=True)
	create_assigned_exception(
		code="ATTENDANCE-CORRECTION",
		description=f"Review corrected Employee Checkin pair {pair_id} for work record {doc.name}.",
		reference_type="Employee Checkin",
		reference_name=created[0],
	)
	return {
		"work_record": doc.name,
		"employee_checkins": created,
		"correction_pair_id": pair_id,
		"status": "Pending Review",
	}


@frappe.whitelist(methods=["POST"])
def review_time_correction(correction_pair_id: str, decision: str, evidence: str):
	"""Approve or reject a pair of proposed standard Employee Checkin records."""
	ensure_roles("Outlet Manager", "HR Manager", "Malaysia HR Manager", "System Manager")
	decision = cstr(decision).strip().title()
	if decision not in {"Approved", "Rejected"}:
		frappe.throw(_("Decision must be Approved or Rejected."))
	evidence = ensure_private_file(evidence, _("Attendance correction evidence"))
	select_for_update(
		"SELECT name FROM `tabEmployee Checkin` WHERE custom_malaysia_correction_pair_id=%s",
		(correction_pair_id,),
	)
	rows = frappe.get_all(
		"Employee Checkin",
		filters={"custom_malaysia_correction_pair_id": correction_pair_id},
		fields=[
			"name",
			"employee",
			"log_type",
			"time",
			"custom_shift_work_record",
			"custom_malaysia_correction_status",
		],
		order_by="time asc",
		limit=10,
	)
	if len(rows) != 2 or {row.log_type for row in rows} != {"IN", "OUT"}:
		frappe.throw(_("A correction must contain exactly one IN and one OUT Employee Checkin."))
	if any(row.custom_malaysia_correction_status != "Pending Review" for row in rows):
		frappe.throw(_("This attendance correction has already been decided."))
	if len({row.employee for row in rows}) != 1 or len({row.custom_shift_work_record for row in rows}) != 1:
		frappe.throw(_("Correction-pair ownership is inconsistent."))
	employee = rows[0].employee
	record_name = rows[0].custom_shift_work_record
	record = frappe.get_doc("Shift Work Record", record_name)
	record.check_permission("write")
	if frappe.db.get_value("Employee", employee, "user_id") == frappe.session.user:
		frappe.throw(_("You cannot approve your own attendance correction."), frappe.PermissionError)
	reviewed_on = now_datetime()
	if decision == "Approved":
		for name in frappe.get_all(
			"Employee Checkin",
			filters={"custom_shift_work_record": record_name, "skip_auto_attendance": 0},
			pluck="name",
			limit=100,
		):
			if name in {row.name for row in rows}:
				continue
			original = frappe.get_doc("Employee Checkin", name)
			original.db_set("skip_auto_attendance", 1, update_modified=True)
			original.add_comment(
				"Comment",
				text=f"Excluded from auto-attendance by approved correction {correction_pair_id}; evidence {evidence}.",
			)
	for row in rows:
		checkin = frappe.get_doc("Employee Checkin", row.name)
		checkin.db_set(
			{
				"skip_auto_attendance": 0 if decision == "Approved" else 1,
				"custom_malaysia_correction_status": decision,
				"custom_malaysia_correction_reviewed_by": frappe.session.user,
				"custom_malaysia_correction_reviewed_on": reviewed_on,
				"custom_malaysia_correction_evidence": evidence,
			},
			update_modified=True,
		)
		checkin.add_comment(
			"Comment",
			text=f"Attendance correction {decision.lower()} by {frappe.session.user}; evidence {evidence}.",
		)
	if decision == "Approved":
		record.db_set(
			{"actual_check_in": None, "actual_check_out": None, "status": "Pending Attendance"},
			update_modified=True,
		)
		reconcile_work_record(record.name)
		existing_attendance = frappe.db.get_value(
			"Attendance",
			{"employee": employee, "attendance_date": record.work_date, "docstatus": 1},
			"name",
		)
		if existing_attendance:
			create_assigned_exception(
				code="ATTENDANCE-REPROCESS",
				description=(
					f"Approved correction {correction_pair_id} affects submitted Attendance "
					f"{existing_attendance}. Reprocess it through standard Frappe HR and retain evidence."
				),
				reference_type="Attendance",
				reference_name=existing_attendance,
			)
	else:
		record.db_set(
			{
				"status": "Employee Correction Required",
				"attendance_exception": f"Attendance correction {correction_pair_id} was rejected.",
			},
			update_modified=True,
		)
	return {"correction_pair_id": correction_pair_id, "decision": decision, "work_record": record.name}


@frappe.whitelist(methods=["POST"])
def approve_work_record(work_record: str, unpaid_break_minutes: int = 0, paid_break_minutes: int = 0):
	ensure_roles("Outlet Manager", "HR Manager", "Malaysia HR Manager", "System Manager")
	doc = frappe.get_doc("Shift Work Record", work_record)
	doc.check_permission("write")
	employee_user = frappe.db.get_value("Employee", doc.employee, "user_id")
	if employee_user and employee_user == frappe.session.user:
		frappe.throw(_("You cannot approve your own attendance record."), frappe.PermissionError)
	if doc.docstatus != 0:
		frappe.throw(_("Only draft work records can be approved."))
	if frappe.db.exists(
		"Employee Checkin",
		{
			"custom_shift_work_record": doc.name,
			"custom_malaysia_correction_status": "Pending Review",
		},
	):
		frappe.throw(_("Review the pending Employee Checkin correction before approving this work record."))
	doc.unpaid_break_minutes = int(unpaid_break_minutes or 0)
	doc.paid_break_minutes = int(paid_break_minutes or 0)
	doc.status = "Approved"
	doc.save()
	doc.submit()
	return {"name": doc.name, "status": doc.status, "gross_pay": doc.gross_pay}
