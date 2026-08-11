from __future__ import annotations

import hashlib
from datetime import timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, get_datetime, getdate, now_datetime

from malaysia_workforce.data_access import get_work_agreement
from malaysia_workforce.staffing.intervals import coerce_time
from malaysia_workforce.utils import stable_json

MANAGER_ROLES = {"Outlet Manager", "HR Manager", "Malaysia HR Manager", "System Manager"}


def _current_employee():
	return frappe.db.get_value(
		"Employee", {"user_id": frappe.session.user, "status": "Active"}, ["name", "company"], as_dict=True
	)


def _minutes(value) -> int:
	time_value = coerce_time(value)
	return time_value.hour * 60 + time_value.minute


class CasualAvailability(Document):
	def validate(self):
		self._set_employee_scope()
		self.cycle_start = getdate(self.cycle_start)
		self.cycle_end = add_days(self.cycle_start, 13)
		self.availability_key = hashlib.sha256(
			f"{self.company}|{self.employee}|{self.cycle_start}".encode()
		).hexdigest()
		self._validate_unique_cycle()
		self._validate_worker()
		self._validate_windows()
		self._set_late_amendment_state()
		self.source_snapshot_hash = hashlib.sha256(self._snapshot().encode()).hexdigest()

	def _set_employee_scope(self):
		current = _current_employee()
		roles = set(frappe.get_roles())
		if not roles & MANAGER_ROLES:
			if not current:
				frappe.throw(_("Your user is not linked to an active Employee."), frappe.PermissionError)
			if self.employee and self.employee != current.name:
				frappe.throw(_("You may only submit your own availability."), frappe.PermissionError)
			self.employee = current.name
			self.company = current.company
		elif self.employee:
			self.company = frappe.db.get_value("Employee", self.employee, "company")

	def _validate_unique_cycle(self):
		existing = frappe.db.get_value(
			"Casual Availability",
			{
				"availability_key": self.availability_key,
				"name": ["!=", self.name],
				"status": "Submitted",
			},
			"name",
		)
		if existing:
			frappe.throw(_("Availability for this cycle already exists: {0}.").format(existing))

	def _validate_worker(self):
		employee = frappe.db.get_value(
			"Employee", self.employee, ["status", "company"], as_dict=True
		)
		if not employee or employee.status != "Active" or employee.company != self.company:
			frappe.throw(_("Availability requires an active Employee in this Company."))
		agreement = get_work_agreement(self.employee, self.cycle_start, required=True)
		if agreement.work_arrangement not in {"Casual", "Part Time"}:
			frappe.throw(_("Availability is only used for casual and part-time agreements."))

	def _validate_windows(self):
		if not self.availability_windows:
			frappe.throw(_("Add at least one availability window."))
		if len(self.availability_windows) > 56:
			frappe.throw(_("A cycle cannot contain more than 56 availability windows."))
		rows = []
		for row in self.availability_windows:
			work_date = getdate(row.work_date)
			if not self.cycle_start <= work_date <= self.cycle_end:
				frappe.throw(_("Row {0} is outside this planning cycle.").format(row.idx))
			start = _minutes(row.available_from)
			end = _minutes(row.available_until)
			if start % 30 or end % 30:
				frappe.throw(_("Availability times must use 30-minute boundaries."))
			if end <= start:
				frappe.throw(_("Availability row {0} must end after it starts.").format(row.idx))
			rows.append((work_date, start, end, row))
		rows.sort(key=lambda item: (item[0], item[1], item[2]))
		for previous, current in zip(rows, rows[1:]):
			if previous[0] == current[0] and current[1] < previous[2]:
				frappe.throw(_("Availability windows on {0} overlap.").format(current[0]))
		self.set("availability_windows", [item[3] for item in rows])

	def _set_late_amendment_state(self):
		closing = frappe.db.get_value(
			"Cafe Staffing Plan",
			{
				"company": self.company,
				"cycle_start": self.cycle_start,
				"docstatus": ["<", 2],
			},
			"availability_closes",
		)
		late = bool(closing and now_datetime() > get_datetime(closing))
		self.late_amendment = int(late)
		if late:
			if not (self.amendment_reason or "").strip():
				frappe.throw(_("Explain why availability is changing after the cutoff."))
			self.manager_review_status = (
				self.workflow_state if self.workflow_state in {"Approved", "Rejected"} else "Pending"
			)
		else:
			self.manager_review_status = "Not Required"
		if self.is_new():
			self.status = "Submitted"
			self.submitted_on = now_datetime()

	def _snapshot(self) -> str:
		return stable_json(
			{
				"employee": self.employee,
				"company": self.company,
				"cycle_start": str(self.cycle_start),
				"cycle_end": str(self.cycle_end),
				"windows": [
					{
						"date": str(row.work_date),
						"from": str(row.available_from),
						"until": str(row.available_until),
					}
					for row in self.availability_windows
				],
				"notes": self.employee_notes or "",
			}
		)

	def on_update(self):
		if not self.late_amendment:
			return
		from malaysia_workforce.compliance.exceptions import create_assigned_exception

		create_assigned_exception(
			code=f"LATE-AVAILABILITY-{self.availability_key[:12]}",
			description=f"Review late availability amendment {self.name} for {self.employee}.",
			reference_type=self.doctype,
			reference_name=self.name,
		)

@frappe.whitelist()
def availability_context(cycle_start=None):
	employee = _current_employee()
	if not employee:
		frappe.throw(_("Your user is not linked to an active Employee."), frappe.PermissionError)
	if cycle_start:
		start = getdate(cycle_start)
	else:
		rows = frappe.get_all(
			"Cafe Staffing Plan",
			filters={
				"company": employee.company,
				"workflow_state": "Collecting Availability",
				"availability_opens": ["<=", now_datetime()],
				"availability_closes": [">=", now_datetime()],
			},
			fields=["cycle_start"],
			order_by="cycle_start asc",
			limit=1,
		)
		start = rows[0].cycle_start if rows else None
		start = getdate(start or getdate())
	return {"employee": employee.name, "company": employee.company, "cycle_start": start, "cycle_end": add_days(start, 13)}


@frappe.whitelist()
def previous_availability_windows(cycle_start):
	employee = _current_employee()
	if not employee:
		frappe.throw(_("Your user is not linked to an active Employee."), frappe.PermissionError)
	previous_start = add_days(getdate(cycle_start), -14)
	name = frappe.db.get_value(
		"Casual Availability",
		{
			"employee": employee.name,
			"company": employee.company,
			"cycle_start": previous_start,
			"status": "Submitted",
		},
		"name",
	)
	if not name:
		return []
	doc = frappe.get_doc("Casual Availability", name)
	return [
		{
			"work_date": add_days(row.work_date, 14),
			"available_from": row.available_from,
			"available_until": row.available_until,
		}
		for row in doc.availability_windows
	]
