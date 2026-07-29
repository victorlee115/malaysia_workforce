from __future__ import annotations

import frappe

from malaysia_workforce.payroll.accumulator import update_accumulator_from_salary_slip


def rebuild_open_accumulators():
	for name in frappe.get_all(
		"Salary Slip",
		filters={"docstatus": 1, "custom_malaysia_statutory_snapshot": ["is", "set"]},
		pluck="name",
		order_by="end_date asc",
		limit_page_length=10000,
	):
		update_accumulator_from_salary_slip(frappe.get_doc("Salary Slip", name))


def generate_statutory_files_for_run(run_name: str) -> dict:
	"""Idempotently generate monthly authority files after the final pay run.

	This job deliberately stops at generation/portal readiness. It never stores portal
	passwords, bypasses OTP, or claims an upload occurred without an official acknowledgement.
	"""
	import json

	import frappe
	from frappe.utils import getdate

	from malaysia_workforce.api.statutory import create_monthly_submissions
	from malaysia_workforce.statutory.submission_service import generate_submission_file

	run = frappe.get_doc("Malaysia Payroll Run", run_name)
	if not run.is_final_run_for_month:
		return {"status": "Skipped", "reason": "Not final pay run for month"}
	if not run.payroll_entry or frappe.db.get_value("Payroll Entry", run.payroll_entry, "docstatus") != 1:
		return {"status": "Skipped", "reason": "Payroll Entry is not submitted"}
	period = getdate(run.end_date)
	created = create_monthly_submissions(
		company=run.company,
		year=period.year,
		month=period.month,
		payroll_run=run.name,
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
	if errors:
		try:
			payload = json.loads(run.validation_errors or "{}")
		except (TypeError, ValueError):
			payload = {}
		payload.setdefault("errors", [])
		payload.setdefault("warnings", [])
		payload["warnings"] = [item for item in payload["warnings"] if not item.startswith("Statutory generation:")]
		payload["warnings"].extend(f"Statutory generation: {item}" for item in errors)
		frappe.db.set_value("Malaysia Payroll Run", run.name, "validation_errors", json.dumps(payload, indent=2), update_modified=True)
		return {"status": "Completed with Errors", "errors": errors, "results": results}
	frappe.db.set_value("Malaysia Payroll Run", run.name, "status", "Statutory Files Generated", update_modified=True)
	return {"status": "Statutory Files Generated", "results": results}
