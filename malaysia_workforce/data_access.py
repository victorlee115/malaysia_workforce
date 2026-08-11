from __future__ import annotations

from datetime import date
from typing import Any

import frappe
from frappe import _
from frappe.utils import getdate


def _active_on(row: dict[str, Any], on_date: date) -> bool:
	start = getdate(row.get("effective_from")) if row.get("effective_from") else getdate("1900-01-01")
	end = getdate(row.get("effective_until")) if row.get("effective_until") else getdate("2999-12-31")
	return start <= on_date <= end


def get_effective_employee_doc(
	doctype: str,
	employee: str,
	on_date,
	*,
	fields: list[str] | None = None,
	required: bool = False,
):
	"""Return the newest employee record whose effective period contains ``on_date``.

	The effective-until predicate is evaluated in Python because SQL NULL/blank handling
	varies across older migrated sites. This also keeps the helper usable by patches.
	"""
	on_date = getdate(on_date)
	query_fields = list(fields or ["*"])
	for fieldname in ("name", "effective_from", "effective_until"):
		if query_fields != ["*"] and fieldname not in query_fields:
			query_fields.append(fieldname)
	rows = frappe.get_all(
		doctype,
		filters={"employee": employee, "effective_from": ["<=", on_date]},
		fields=query_fields,
		order_by="effective_from desc, modified desc",
		limit=100,
	)
	for row in rows:
		if _active_on(row, on_date):
			return row
	if required:
		frappe.throw(
			_("No active {0} was found for employee {1} on {2}.").format(doctype, employee, on_date)
		)
	return None


def get_work_agreement(employee: str, on_date, *, required: bool = False):
	return get_effective_employee_doc("Employee Work Agreement", employee, on_date, required=required)


def get_statutory_profile(employee: str, on_date, *, required: bool = False):
	row = get_effective_employee_doc("Statutory Coverage Profile", employee, on_date, required=required)
	return frappe.get_doc("Statutory Coverage Profile", row.name) if row else None


def get_malaysia_profile(employee: str, *, required: bool = False):
	name = frappe.db.get_value("Malaysia Employee Profile", {"employee": employee}, "name")
	if not name and required:
		frappe.throw(_("Malaysia Employee Profile is missing for employee {0}.").format(employee))
	return frappe.get_doc("Malaysia Employee Profile", name) if name else None


def get_scheme_treatment(employee: str, scheme: str, on_date) -> tuple[str, str, str]:
	profile = get_statutory_profile(employee, on_date)
	if not profile:
		return "Automatic", "", ""
	on_date = getdate(on_date)
	for line in profile.coverage_lines:
		if line.scheme != scheme:
			continue
		start = getdate(line.effective_from or profile.effective_from)
		end = getdate(line.effective_until or profile.effective_until or "2999-12-31")
		if start <= on_date <= end:
			return line.treatment or "Automatic", line.reason_code or "", line.notes or ""
	return "Automatic", "", ""
