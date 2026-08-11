from __future__ import annotations

import hashlib

import frappe
from malaysia_workforce.payroll.accumulator import _accumulator_key
from malaysia_workforce.setup.master_data import COMPONENTS


PRODUCTION_CONTROL_SCHEMA_VERSION = 5
LEGACY_DOCTYPES = (
	"Roster Standby",
	"Roster Selection",
	"Roster Application",
	"Roster Availability Window",
	"Roster Coverage Requirement",
	"Casual Roster",
	"Malaysia Payroll Run",
)
LEGACY_CUSTOM_FIELDS = (
	"Employee-custom_work_arrangement",
	"Employee-custom_roster_enabled",
	"Employee-custom_malaysia_legal_jurisdiction",
	"Employee Checkin-custom_roster_selection",
	"Shift Assignment-custom_roster_selection",
	"Shift Assignment-custom_assigned_start_datetime",
	"Shift Assignment-custom_assigned_end_datetime",
	"Shift Assignment-custom_assigned_role",
	"Salary Slip-custom_malaysia_payroll_run",
	"Payroll Entry-custom_malaysia_payroll_run",
	"Journal Entry-custom_malaysia_payroll_run",
)


def preflight_legacy_cleanup() -> None:
	"""Stop before schema sync if obsolete production records would be orphaned."""
	populated = []
	for doctype in LEGACY_DOCTYPES:
		table = f"tab{doctype}"
		if frappe.db.table_exists(doctype) and frappe.db.sql(f"SELECT COUNT(*) FROM `{table}`")[0][0]:
			populated.append(doctype)
	if populated:
		frappe.throw(
			"Malaysia Workforce cannot remove the release-candidate roster/payroll schema because records exist in: "
			+ ", ".join(populated)
			+ ". Export and reconcile these records before upgrading."
		)


def _remove_empty_legacy_schema() -> None:
	for fieldname in LEGACY_CUSTOM_FIELDS:
		if frappe.db.exists("Custom Field", fieldname):
			frappe.delete_doc("Custom Field", fieldname, ignore_permissions=True, force=True)
	for doctype in LEGACY_DOCTYPES:
		if frappe.db.exists("DocType", doctype):
			frappe.delete_doc("DocType", doctype, ignore_permissions=True, force=True)
	if frappe.db.exists("Role", "Roster Manager") and not frappe.db.exists("Has Role", {"role": "Roster Manager"}):
		frappe.delete_doc("Role", "Roster Manager", ignore_permissions=True, force=True)


def apply_production_control_backfill() -> None:
	"""One-time, idempotent backfill after dynamic custom fields are synchronized."""
	settings = frappe.get_single("Malaysia Workforce Settings")
	if int(settings.production_control_schema_version or 0) >= PRODUCTION_CONTROL_SCHEMA_VERSION:
		return

	_remove_empty_legacy_schema()

	for name, values in COMPONENTS.items():
		if not frappe.db.exists("Salary Component", name):
			continue
		doc = frappe.get_doc("Salary Component", name)
		if not int(doc.custom_malaysia_component or 0):
			continue
		updates = {}
		if values["type"] == "Earning" and values.get("hrd"):
			updates["custom_include_in_hrd_levy_wages"] = 1
		if values["type"] == "Deduction" and not doc.custom_malaysia_deduction_basis:
			updates["custom_malaysia_deduction_basis"] = (
				"Employee Written Request" if name == "Zakat" else "Written Law"
			)
		if updates:
			frappe.db.set_value("Salary Component", name, updates, update_modified=False)

	default_review = settings.rules_reviewed_through
	for company in frappe.get_all(
		"Company",
		filters={"custom_enable_malaysia_payroll": 1},
		fields=["name", "custom_malaysia_rule_review_deadline"],
	):
		if not company.custom_malaysia_rule_review_deadline and default_review:
			frappe.db.set_value(
				"Company", company.name, "custom_malaysia_rule_review_deadline", default_review, update_modified=False
			)

	seen_accumulators: dict[str, str] = {}
	for row in frappe.get_all(
		"Monthly Statutory Accumulator",
		fields=["name", "employee", "company", "contribution_month"],
		limit=100000,
	):
		key = _accumulator_key(row.employee, row.company, row.contribution_month)
		if key in seen_accumulators:
			frappe.throw(
				f"Duplicate statutory accumulators require controlled reconciliation: {seen_accumulators[key]}, {row.name}"
			)
		seen_accumulators[key] = row.name
		frappe.db.set_value("Monthly Statutory Accumulator", row.name, "accumulator_key", key, update_modified=False)

	seen_submissions: dict[str, str] = {}
	for row in frappe.get_all(
		"Statutory Submission",
		fields=["name", "company", "authority", "submission_type", "contribution_year", "contribution_month", "revision"],
		limit=100000,
	):
		key = hashlib.sha256(
			f"{row.company}|{row.authority}|{row.submission_type}|{row.contribution_year}|{int(row.contribution_month or 0)}|{int(row.revision or 0)}".encode()
		).hexdigest()
		if key in seen_submissions:
			frappe.throw(
				f"Duplicate statutory submission revisions require controlled reconciliation: {seen_submissions[key]}, {row.name}"
			)
		seen_submissions[key] = row.name
		frappe.db.set_value("Statutory Submission", row.name, "submission_key", key, update_modified=False)

	statements: dict[tuple[str, str, int, str], list] = {}
	for row in frappe.get_all(
		"Malaysia Annual Remuneration Statement",
		fields=["name", "employee", "company", "tax_year", "form_type", "creation"],
		order_by="creation asc, name asc",
		limit=100000,
	):
		statements.setdefault((row.company, row.employee, int(row.tax_year), row.form_type), []).append(row)
	for (company, employee, tax_year, form_type), rows in statements.items():
		for revision, row in enumerate(rows):
			key = hashlib.sha256(
				f"{company}|{employee}|{tax_year}|{form_type}|{revision}".encode()
			).hexdigest()
			frappe.db.set_value(
				"Malaysia Annual Remuneration Statement",
				row.name,
				{"revision": revision, "statement_key": key},
				update_modified=False,
			)

	frappe.db.set_single_value(
		"Malaysia Workforce Settings",
		"production_control_schema_version",
		PRODUCTION_CONTROL_SCHEMA_VERSION,
	)
