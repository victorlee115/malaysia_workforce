from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation, ROUND_DOWN, ROUND_UP
from typing import Any

import frappe
from frappe import _
from frappe.utils import get_datetime, getdate

MONEY_QUANTUM = Decimal("0.01")


def as_decimal(value: Any, default: str = "0") -> Decimal:
	"""Convert values to a finite Decimal.

	Payroll and statutory calculations must reject NaN and infinity rather than
	allowing them to bypass ordinary range comparisons.
	"""
	try:
		result = Decimal(default) if value is None or value == "" else (value if isinstance(value, Decimal) else Decimal(str(value)))
	except (InvalidOperation, TypeError, ValueError) as exc:
		raise ValueError(f"Invalid decimal value: {value!r}") from exc
	if not result.is_finite():
		raise ValueError(f"Decimal value must be finite: {value!r}")
	return result


def validate_decimal(
	value: Any,
	label: str,
	*,
	minimum: Any | None = None,
	maximum: Any | None = None,
	allow_blank: bool = True,
) -> Decimal | None:
	"""Validate a user-entered number and return it as a finite Decimal."""
	if allow_blank and (value is None or value == ""):
		return None
	try:
		result = as_decimal(value)
	except ValueError:
		frappe.throw(_("{0} must be a finite number.").format(label))
	if minimum is not None and result < as_decimal(minimum):
		frappe.throw(_("{0} cannot be below {1}.").format(label, minimum))
	if maximum is not None and result > as_decimal(maximum):
		frappe.throw(_("{0} cannot exceed {1}.").format(label, maximum))
	return result


def money(value: Any) -> Decimal:
	return as_decimal(value).quantize(MONEY_QUANTUM)


def truncate(value: Any, places: int = 2) -> Decimal:
	quantum = Decimal(1).scaleb(-places)
	return as_decimal(value).quantize(quantum, rounding=ROUND_DOWN)


def ceil_ringgit(value: Any) -> Decimal:
	return as_decimal(value).quantize(Decimal("1"), rounding=ROUND_UP)


def sha256_bytes(data: bytes) -> str:
	return hashlib.sha256(data).hexdigest()


def stable_json(data: Any) -> str:
	return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def combine_date_time(value_date: date | str, value_time: time | str) -> datetime:
	day = getdate(value_date)
	if isinstance(value_time, str):
		parsed = get_datetime(f"2000-01-01 {value_time}").time()
	else:
		parsed = value_time
	return datetime.combine(day, parsed)


def end_after_start(start: datetime, end: datetime) -> datetime:
	return end + timedelta(days=1) if end <= start else end


def ensure_roles(*allowed: str) -> None:
	if "System Manager" in frappe.get_roles():
		return
	if not set(allowed).intersection(frappe.get_roles()):
		frappe.throw(_("You do not have permission to perform this action."), frappe.PermissionError)


def get_current_employee(required: bool = True) -> str | None:
	if frappe.session.user == "Guest":
		if required:
			frappe.throw(_("Please sign in."), frappe.PermissionError)
		return None
	employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user, "status": "Active"}, "name")
	if not employee and required:
		frappe.throw(_("Your user account is not linked to an active Employee record."), frappe.PermissionError)
	return employee


def validate_date_range(start, end, label: str = "date range") -> None:
	if start and end and getdate(end) < getdate(start):
		frappe.throw(_("End date cannot be before start date for {0}.").format(label))
