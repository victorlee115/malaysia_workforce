from __future__ import annotations

import frappe
from frappe import _

from malaysia_workforce.staffing.intervals import coerce_time
from malaysia_workforce.staffing.shift_identity import managed_shift_identity


def _canonical(value) -> str:
	parsed = coerce_time(value)
	return parsed.strftime("%H:%M:%S")


def get_or_create_managed_shift_type(start_time, end_time) -> str:
	settings = frappe.get_cached_doc("Malaysia Workforce Settings")
	template_name = settings.flexible_shift_template
	if not template_name or not frappe.db.exists("Shift Type", template_name):
		frappe.throw(_("Configure a Base Casual Shift Type in Malaysia Workforce Settings."))
	name, fingerprint = managed_shift_identity(template_name, start_time, end_time)
	existing = frappe.db.get_value(
		"Shift Type",
		{"custom_malaysia_shift_fingerprint": fingerprint},
		["name", "start_time", "end_time", "custom_malaysia_shift_template"],
		as_dict=True,
	)
	if existing:
		if (
			_canonical(existing.start_time) != _canonical(start_time)
			or _canonical(existing.end_time) != _canonical(end_time)
			or existing.custom_malaysia_shift_template != template_name
		):
			frappe.throw(_("Managed Shift Type fingerprint collision: {0}.").format(existing.name))
		return existing.name

	template = frappe.get_doc("Shift Type", template_name)
	doc = frappe.new_doc("Shift Type")
	doc.name = name
	copy_fields = (
		"enable_auto_attendance",
		"determine_check_in_and_check_out",
		"working_hours_calculation_based_on",
		"begin_check_in_before_shift_start_time",
		"allow_check_out_after_shift_end_time",
		"mark_auto_attendance_on_holidays",
		"working_hours_threshold_for_half_day",
		"working_hours_threshold_for_absent",
		"late_entry_grace_period",
		"enable_late_entry_marking",
		"early_exit_grace_period",
		"enable_early_exit_marking",
		"color",
	)
	valid_fields = {field.fieldname for field in frappe.get_meta("Shift Type").fields}
	for fieldname in copy_fields:
		if fieldname in valid_fields:
			doc.set(fieldname, template.get(fieldname))
	doc.start_time = _canonical(start_time)
	doc.end_time = _canonical(end_time)
	doc.custom_malaysia_managed_shift = 1
	doc.custom_malaysia_shift_template = template_name
	doc.custom_malaysia_shift_fingerprint = fingerprint
	doc.insert(ignore_permissions=True)
	return doc.name


def prevent_managed_shift_deletion(doc, method=None):
	if not getattr(doc, "custom_malaysia_managed_shift", 0):
		return
	if frappe.db.exists("Shift Assignment", {"shift_type": doc.name, "docstatus": ["<", 2]}):
		frappe.throw(_("This managed Shift Type is used by a Shift Assignment and cannot be deleted."))
