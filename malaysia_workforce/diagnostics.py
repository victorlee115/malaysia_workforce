from __future__ import annotations

import hashlib
import json
from pathlib import Path

import frappe
from frappe.utils import add_days, add_to_date, get_datetime, getdate, now_datetime, today

from malaysia_workforce import __version__
from malaysia_workforce.setup.master_data import COMPONENTS, ROLES
from malaysia_workforce.statutory.common import DATA_DIR


def _version(module_name: str) -> str | None:
	try:
		module = __import__(module_name)
		return getattr(module, "__version__", None)
	except Exception:
		return None


def _rule_data_check() -> dict:
	manifest_path = DATA_DIR / "source_manifest.json"
	manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
	files = {}
	for filename, expected in manifest.get("generated_tables", {}).items():
		path = DATA_DIR / filename
		actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
		files[filename] = {
			"exists": path.exists(),
			"expected_sha256": expected.get("sha256"),
			"actual_sha256": actual,
			"valid": bool(actual and actual == expected.get("sha256")),
		}
	return {"valid": all(row["valid"] for row in files.values()), "files": files}


def _company_check(company: str) -> dict:
	row = frappe.db.get_value(
		"Company",
		company,
		[
			"country",
			"default_currency",
			"default_payroll_payable_account",
			"default_holiday_list",
			"custom_enable_malaysia_payroll",
			"custom_lhdn_hq_number",
			"custom_lhdn_employer_number",
			"custom_epf_employer_number",
			"custom_socso_employer_code",
			"custom_malaysia_jurisdiction",
			"custom_malaysia_production_activated",
			"custom_malaysia_activation_evidence",
			"custom_malaysia_privacy_notice",
			"custom_malaysia_privacy_notice_version",
			"custom_hrd_corp_registered",
			"custom_hrd_corp_registration_number",
			"custom_hrd_levy_rate",
			"custom_malaysia_rule_review_deadline",
			"custom_malaysia_bank_file_format",
			"custom_malaysia_bank_uat_evidence",
			"custom_malaysia_last_backup_on",
			"custom_malaysia_backup_encrypted",
			"custom_malaysia_backup_evidence",
			"custom_malaysia_last_restore_test",
		],
		as_dict=True,
	)
	if not row:
		return {"company": company, "exists": False, "errors": ["Company does not exist"]}
	errors = []
	if row.country != "Malaysia":
		errors.append("Country is not Malaysia")
	if row.default_currency != "MYR":
		errors.append("Default currency is not MYR")
	if not row.custom_enable_malaysia_payroll:
		errors.append("Malaysia Payroll is not enabled")
	if row.custom_malaysia_jurisdiction != "Peninsular Malaysia":
		errors.append("Supported jurisdiction is not Peninsular Malaysia")
	if not row.custom_malaysia_rule_review_deadline or getdate(row.custom_malaysia_rule_review_deadline) < getdate():
		errors.append("Company statutory rule review is missing or expired")
	if not row.default_payroll_payable_account:
		errors.append("Default Payroll Payable Account is missing")
	for fieldname, label in (
		("custom_lhdn_hq_number", "LHDN HQ Number"),
		("custom_lhdn_employer_number", "LHDN Employer Number"),
		("custom_epf_employer_number", "EPF Employer Number"),
		("custom_socso_employer_code", "SOCSO Employer Code"),
	):
		if not row.get(fieldname):
			errors.append(f"{label} is missing")
	headcount = frappe.db.count("Employee", {"company": company, "status": "Active"})
	if headcount >= 10 and (not row.custom_hrd_corp_registered or not row.custom_hrd_corp_registration_number):
		errors.append("HRD Corp registration is incomplete for 10+ active employees")
	if headcount >= 10 and float(row.custom_hrd_levy_rate or 0) != 1:
		errors.append("The reviewed HRD Corp levy rate for this 10+ employee deployment must be 1%")
	if row.custom_malaysia_production_activated:
		if not row.custom_malaysia_activation_evidence:
			errors.append("Production activation evidence is missing")
		if not row.custom_malaysia_privacy_notice or not row.custom_malaysia_privacy_notice_version:
			errors.append("A versioned Malaysia employee privacy notice is missing")
		if row.custom_malaysia_bank_file_format in {None, "", "Not Configured", "Generic CSV (UAT Only)"}:
			errors.append("A production bank-specific adapter is not configured")
		else:
			from malaysia_workforce.banking.service import production_bank_adapter_available

			if not production_bank_adapter_available(row.custom_malaysia_bank_file_format):
				errors.append("The configured production bank adapter hook is not installed")
		if not row.custom_malaysia_bank_uat_evidence:
			errors.append("Bank UAT evidence is missing")
	if not row.custom_malaysia_last_restore_test or getdate(row.custom_malaysia_last_restore_test) < getdate(add_days(today(), -90)):
		errors.append("No successful backup restore test is recorded in the last 90 days")
	if (
		not row.custom_malaysia_last_backup_on
		or get_datetime(row.custom_malaysia_last_backup_on) < add_to_date(now_datetime(), hours=-24)
		or not row.custom_malaysia_backup_encrypted
		or not row.custom_malaysia_backup_evidence
	):
		errors.append("No verified encrypted backup is recorded in the last 24 hours")

	try:
		from malaysia_workforce.compliance.scope import assert_payroll_accounts_configured

		assert_payroll_accounts_configured(company)
	except Exception as exc:
		errors.append(f"Payroll accounts are incomplete: {exc}")

	missing_employee_controls = frappe.get_all(
		"Employee",
		filters={
			"company": company,
			"status": "Active",
		},
		fields=[
			"name",
			"holiday_list",
			"custom_malaysia_privacy_acknowledgement",
			"custom_malaysia_privacy_notice_version",
			"custom_employee_work_agreement",
			"custom_malaysia_employee_profile",
			"custom_statutory_coverage_profile",
		],
		limit=100000,
	)
	missing = {
		"work_agreement": [r.name for r in missing_employee_controls if not r.custom_employee_work_agreement],
		"malaysia_profile": [r.name for r in missing_employee_controls if not r.custom_malaysia_employee_profile],
		"coverage_profile": [r.name for r in missing_employee_controls if not r.custom_statutory_coverage_profile],
		"holiday_list": [r.name for r in missing_employee_controls if not r.holiday_list and not row.default_holiday_list],
		"leave_policy_assignment": [
			r.name
			for r in missing_employee_controls
			if not frappe.db.exists("Leave Policy Assignment", {"employee": r.name, "docstatus": 1})
		],
		"privacy_acknowledgement": [
			r.name
			for r in missing_employee_controls
			if not r.custom_malaysia_privacy_acknowledgement
			or r.custom_malaysia_privacy_notice_version != row.custom_malaysia_privacy_notice_version
		],
	}
	for label, names in missing.items():
		if names:
			errors.append(f"{len(names)} active employee(s) missing {label.replace('_', ' ')}")
	return {
		"company": company,
		"exists": True,
		"active_headcount": headcount,
		"production_activated": bool(row.custom_malaysia_production_activated),
		"missing_employee_controls": missing,
		"errors": errors,
		"ready": not errors,
	}


def _operations_check() -> dict:
	settings = frappe.get_cached_doc("Malaysia Workforce Settings")
	site_time_zone = frappe.db.get_single_value("System Settings", "time_zone")
	site_country = frappe.defaults.get_global_default("country") or frappe.db.get_single_value(
		"Global Defaults", "country"
	)
	site_currency = frappe.defaults.get_global_default("currency") or frappe.db.get_single_value(
		"Global Defaults", "default_currency"
	)
	methods = {
		"refresh_obligations": "malaysia_workforce.compliance.jobs.refresh_obligations",
		"control_deadlines": "malaysia_workforce.compliance.jobs.refresh_control_deadlines",
		"attendance_reconcile": "malaysia_workforce.attendance.jobs.reconcile_recent_work_records",
		"availability_reminders": "malaysia_workforce.staffing.jobs.send_availability_reminders",
		"staffing_deadlines": "malaysia_workforce.staffing.jobs.flag_staffing_deadlines",
		"stale_staffing_proposals": "malaysia_workforce.staffing.jobs.flag_stale_staffing_proposals",
		"staffing_priority_expiry": "malaysia_workforce.staffing.jobs.expire_staffing_priorities",
		"accumulator_rebuild": "malaysia_workforce.payroll.jobs.rebuild_open_accumulators",
	}
	registered = {
		name: bool(frappe.db.exists("Scheduled Job Type", {"method": method}))
		for name, method in methods.items()
	}
	worker_count = None
	try:
		if frappe.db.table_exists("RQ Worker"):
			worker_count = frappe.db.count("RQ Worker")
	except Exception:
		worker_count = None
	pending_exceptions = frappe.db.count(
		"ToDo", {"status": "Open", "custom_malaysia_exception_code": ["is", "set"]}
	)
	pending_submissions = frappe.db.count(
		"Statutory Submission", {"status": ["in", ["Validation Failed", "Rejected"]]}
	)
	rule_review_expired = bool(
		not settings.rules_reviewed_through
		or getdate(settings.rules_reviewed_through) < getdate(today())
	)
	worker_health_verified = bool(worker_count is not None and worker_count > 0)
	kiosk_stale = bool(
		settings.kiosk_enabled
		and (
			not settings.kiosk_last_seen_on
			or getdate(settings.kiosk_last_seen_on) < getdate(add_days(today(), -1))
		)
	)
	base_shift = settings.flexible_shift_template
	base_shift_row = (
		frappe.db.get_value(
			"Shift Type", base_shift, ["name", "enable_auto_attendance", "custom_malaysia_managed_shift"], as_dict=True
		)
		if base_shift
		else None
	)
	base_shift_valid = bool(base_shift_row and not base_shift_row.custom_malaysia_managed_shift)
	collecting_plans = frappe.db.count("Cafe Staffing Plan", {"workflow_state": "Collecting Availability"})
	staffing_plans_with_gaps = frappe.db.count(
		"Cafe Staffing Plan",
		{"workflow_state": ["in", ["Proposed", "Approved"]], "unresolved_exception_count": [">", 0]},
	)
	return {
		"site_time_zone": site_time_zone,
		"site_time_zone_supported": site_time_zone == "Asia/Kuala_Lumpur",
		"site_country": site_country,
		"site_country_supported": site_country == "Malaysia",
		"site_currency": site_currency,
		"site_currency_supported": site_currency == "MYR",
		"scheduler_disabled": bool(getattr(frappe.conf, "disable_scheduler", False)),
		"scheduled_jobs_registered": registered,
		"worker_count": worker_count,
		"worker_health_verified": worker_health_verified,
		"rule_review_expired": rule_review_expired,
		"kiosk_stale": kiosk_stale,
		"base_casual_shift_type": base_shift,
		"base_casual_shift_valid": base_shift_valid,
		"base_casual_shift_auto_attendance": bool(base_shift_row and base_shift_row.enable_auto_attendance),
		"availability_collection_plans": collecting_plans,
		"staffing_plans_with_gaps": staffing_plans_with_gaps,
		"pending_assigned_exceptions": pending_exceptions,
		"failed_or_rejected_submissions": pending_submissions,
		"ready": bool(
			site_time_zone == "Asia/Kuala_Lumpur"
			and site_country == "Malaysia"
			and site_currency == "MYR"
			and not getattr(frappe.conf, "disable_scheduler", False)
			and all(registered.values())
			and worker_health_verified
			and not rule_review_expired
			and not kiosk_stale
			and base_shift_valid
			and staffing_plans_with_gaps == 0
			and pending_exceptions == 0
			and pending_submissions == 0
		),
	}


def run(company: str | None = None) -> dict:
	"""Return a read-only installation/configuration health report.

	Usage: bench --site <site> execute malaysia_workforce.diagnostics.run --kwargs '{"company":"Example Sdn Bhd"}'
	"""
	installed = set(frappe.get_installed_apps())
	settings_exists = frappe.db.exists("DocType", "Malaysia Workforce Settings")
	missing_roles = [name for name in ROLES if not frappe.db.exists("Role", name)]
	missing_components = [name for name in COMPONENTS if not frappe.db.exists("Salary Component", name)]
	companies = [company] if company else frappe.get_all(
		"Company", filters={"custom_enable_malaysia_payroll": 1}, pluck="name", order_by="name"
	)
	operations = _operations_check() if settings_exists else {"ready": False}
	report = {
		"app_version": __version__,
		"versions": {
			"frappe": getattr(frappe, "__version__", None),
			"erpnext": _version("erpnext"),
			"hrms": _version("hrms"),
		},
		"installed_apps_ok": {app: app in installed for app in ("frappe", "erpnext", "hrms", "malaysia_workforce")},
		"settings_exists": bool(settings_exists),
		"missing_roles": missing_roles,
		"missing_salary_components": missing_components,
		"rule_data": _rule_data_check(),
		"companies": [_company_check(name) for name in companies],
		"operations": operations,
	}
	report["ok"] = bool(
		all(report["installed_apps_ok"].values())
		and report["settings_exists"]
		and not missing_roles
		and not missing_components
		and report["rule_data"]["valid"]
		and bool(companies)
		and all(row.get("ready") for row in report["companies"])
		and operations.get("ready")
	)
	return report


def assert_ready(company: str | None = None) -> dict:
	"""Fail the command when installation or company readiness checks are incomplete."""
	report = run(company)
	if not report.get("ok"):
		frappe.throw(
			"Malaysia Workforce readiness checks failed:\n"
			+ json.dumps(report, indent=2, default=str),
			title="Malaysia Workforce Not Ready",
		)
	return report


def assert_compatible_stack() -> dict:
	lock = json.loads((Path(__file__).resolve().parents[1] / "compatibility-lock.json").read_text())
	actual = {
		"frappe": getattr(frappe, "__version__", None),
		"erpnext": _version("erpnext"),
		"hrms": _version("hrms"),
	}
	expected = {name: row["version"] for name, row in lock["apps"].items()}
	if actual != expected:
		frappe.throw(f"Pinned stack mismatch: expected {expected}, got {actual}")
	return {"compatible": True, "expected": expected, "actual": actual}
