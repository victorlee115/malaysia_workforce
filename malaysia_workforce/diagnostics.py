from __future__ import annotations

import hashlib
import json
from pathlib import Path

import frappe

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
			"custom_enable_malaysia_payroll",
			"custom_lhdn_hq_number",
			"custom_lhdn_employer_number",
			"custom_epf_employer_number",
			"custom_socso_employer_code",
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
	return {"company": company, "exists": True, "errors": errors, "ready": not errors}


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
	}
	report["ok"] = bool(
		all(report["installed_apps_ok"].values())
		and report["settings_exists"]
		and not missing_roles
		and not missing_components
		and report["rule_data"]["valid"]
		and all(row.get("ready") for row in report["companies"])
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
