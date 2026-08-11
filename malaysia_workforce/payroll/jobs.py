from __future__ import annotations

import frappe

from malaysia_workforce.payroll.accumulator import update_accumulator_from_salary_slip
from malaysia_workforce.compliance.exceptions import create_assigned_exception


def rebuild_open_accumulators():
	for name in frappe.get_all(
		"Salary Slip",
		filters={"docstatus": 1, "custom_malaysia_statutory_snapshot": ["is", "set"]},
		pluck="name",
		order_by="end_date asc",
		limit=10000,
	):
		try:
			update_accumulator_from_salary_slip(frappe.get_doc("Salary Slip", name))
		except Exception as exc:
			frappe.log_error(title=f"Statutory accumulator rebuild failed: {name}", message=frappe.get_traceback())
			try:
				create_assigned_exception(
					code="ACCUMULATOR-REBUILD",
					description=f"Resolve statutory accumulator rebuild failure for {name}: {exc}",
					reference_type="Salary Slip",
					reference_name=name,
				)
			except Exception:
				frappe.log_error(title=f"Accumulator exception assignment failed: {name}", message=frappe.get_traceback())


def generate_statutory_files_for_payroll_entry(payroll_entry: str) -> dict:
	"""Idempotently generate authority files from the standard Payroll Entry.

	This job deliberately stops at generation/portal readiness. It never stores portal
	passwords, bypasses OTP, or claims an upload occurred without an official acknowledgement.
	"""
	import json

	import frappe
	from frappe.utils import getdate

	from malaysia_workforce.api.statutory import create_monthly_submissions
	from malaysia_workforce.statutory.submission_service import generate_submission_file

	entry = frappe.get_doc("Payroll Entry", payroll_entry)
	if not entry.custom_malaysia_final_run:
		return {"status": "Skipped", "reason": "Not final pay run for month"}
	if entry.docstatus != 1:
		return {"status": "Skipped", "reason": "Payroll Entry is not submitted"}
	period = getdate(entry.end_date)
	created = create_monthly_submissions(
		company=entry.company,
		year=period.year,
		month=period.month,
		payroll_entry=entry.name,
	)
	results = {}
	errors = []
	for name in created:
		try:
			results[name] = generate_submission_file(frappe.get_doc("Statutory Submission", name))
		except Exception as exc:
			frappe.log_error(
				title=f"Malaysia statutory generation failed for {name}",
				message=frappe.get_traceback(),
			)
			errors.append(f"{name}: {exc}")
			try:
				create_assigned_exception(
					code="STATUTORY-FILE-GENERATION",
					description=f"Resolve statutory file generation failure for {name}: {exc}",
					reference_type="Statutory Submission",
					reference_name=name,
				)
			except Exception:
				frappe.log_error(title=f"Statutory exception assignment failed: {name}", message=frappe.get_traceback())
	if errors:
		try:
			payload = json.loads(entry.custom_malaysia_validation_errors or "{}")
		except (TypeError, ValueError):
			payload = {}
		payload.setdefault("errors", [])
		payload.setdefault("warnings", [])
		payload["warnings"] = [item for item in payload["warnings"] if not item.startswith("Statutory generation:")]
		payload["warnings"].extend(f"Statutory generation: {item}" for item in errors)
		frappe.db.set_value(
			"Payroll Entry",
			entry.name,
			{
				"custom_malaysia_validation_errors": json.dumps(payload, indent=2),
				"custom_malaysia_statutory_preparation_status": "Validation Failed",
			},
			update_modified=True,
		)
		return {"status": "Completed with Errors", "errors": errors, "results": results}
	frappe.db.set_value(
		"Payroll Entry",
		entry.name,
		"custom_malaysia_statutory_preparation_status",
		"Generated",
		update_modified=True,
	)
	return {"status": "Statutory Files Generated", "results": results}
