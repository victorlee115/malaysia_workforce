from __future__ import annotations

import hashlib
import json
from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import add_days, add_to_date, get_datetime, get_first_day, getdate, now_datetime

SUPPORTED_JURISDICTION = "Peninsular Malaysia"
SUPPORTED_ARRANGEMENTS = {"Full Time", "Part Time", "Casual"}
SUPPORTED_CONTRACT_RELATIONSHIP = "Contract of Service"


def malaysia_payroll_enabled(company: str | None) -> bool:
	return bool(company and frappe.db.get_value("Company", company, "custom_enable_malaysia_payroll"))


def assert_payroll_accounts_configured(company: str) -> dict:
	"""Validate standard component accounts and the separate employer-cost accounts."""
	from malaysia_workforce.setup.master_data import COMPONENTS

	component_rows = frappe.get_all(
		"Salary Component Account",
		filters={"company": company, "parent": ["in", list(COMPONENTS)]},
		fields=["parent", "account"],
		order_by="parent, account",
		limit=100000,
	)
	component_accounts = {row.parent: row.account for row in component_rows if row.account}
	missing = [
		name
		for name, definition in COMPONENTS.items()
		if definition["type"] in {"Earning", "Deduction"}
		and name not in component_accounts
	]
	if missing:
		frappe.throw(_("Malaysia Salary Component accounts are missing: {0}.").format(", ".join(missing)))
	from malaysia_workforce.payroll.services import employer_contribution_account_map

	employer_accounts = employer_contribution_account_map(company)
	return {
		"salary_components": component_accounts,
		"employer_contributions": {
			scheme: list(accounts) for scheme, accounts in sorted(employer_accounts.items())
		},
	}


def allowed_nationalities(company: str) -> set[str]:
	policy = frappe.db.get_value("Company", company, "custom_malaysia_citizenship_policy")
	if policy == "Malaysian Citizens and Permanent Residents":
		return {"Malaysian", "Permanent Resident"}
	return {"Malaysian"}


def assert_rule_review_current(company: str, on_date) -> None:
	on_date = getdate(on_date)
	settings = frappe.get_cached_doc("Malaysia Workforce Settings")
	if settings.strict_rule_review and (
		not settings.rules_reviewed_through
		or getdate(settings.rules_reviewed_through) < on_date
	):
		frappe.throw(
			_("Malaysia statutory rule review is missing or expired for {0}.").format(on_date),
			title=_("Statutory Rule Review Expired"),
		)
	company_deadline = frappe.db.get_value("Company", company, "custom_malaysia_rule_review_deadline")
	if not company_deadline or getdate(company_deadline) < on_date:
		frappe.throw(
			_("Company statutory rule review is missing or expired for {0}.").format(on_date),
			title=_("Statutory Rule Review Expired"),
		)


def validate_employee_scope(doc, method=None) -> None:
	if not malaysia_payroll_enabled(getattr(doc, "company", None)) or getattr(doc, "status", None) != "Active":
		return
	agreement_name = getattr(doc, "custom_employee_work_agreement", None)
	if not agreement_name:
		frappe.throw(_("Employee Work Agreement is required before activating this Employee."))
	agreement = frappe.get_doc("Employee Work Agreement", agreement_name)
	if agreement.employee != doc.name or agreement.company != doc.company:
		frappe.throw(_("Current Work Agreement must belong to this Employee and Company."))
	validate_work_agreement_scope(agreement)
	profile = frappe.db.get_value(
		"Malaysia Employee Profile",
		{"employee": doc.name},
		["name", "nationality_status", "tax_regime"],
		as_dict=True,
	)
	if not profile:
		frappe.throw(_("Create a Malaysia Employee Profile before activating this Employee."))
	if profile.nationality_status not in allowed_nationalities(doc.company):
		frappe.throw(
			_("Nationality status {0} is outside this Company's activated Malaysia payroll scope.").format(
				profile.nationality_status
			),
			title=_("Unsupported Citizenship"),
		)
	if profile.tax_regime != "STANDARD":
		frappe.throw(_("Only the STANDARD PCB tax regime is implemented and approved for production."))
	for fieldname, label in (("custom_statutory_coverage_profile", _("Statutory Coverage Profile")),):
		if not getattr(doc, fieldname, None):
			frappe.throw(_("{0} is required before activating this Employee.").format(label))


def validate_work_agreement_scope(doc) -> None:
	if not malaysia_payroll_enabled(getattr(doc, "company", None)):
		return
	if doc.jurisdiction != SUPPORTED_JURISDICTION:
		frappe.throw(_("Only Peninsular Malaysia work agreements are supported in this release."))
	if doc.contract_relationship != SUPPORTED_CONTRACT_RELATIONSHIP:
		frappe.throw(
			_("Use standard supplier/contractor processes for a Contract for Service; it is not employee payroll."),
			title=_("Unsupported Contract Relationship"),
		)
	if doc.work_arrangement not in SUPPORTED_ARRANGEMENTS:
		frappe.throw(_("Work arrangement {0} is not supported in this release.").format(doc.work_arrangement))


def assert_employee_supported(employee: str, company: str) -> None:
	row = frappe.db.get_value(
		"Employee",
		employee,
		[
			"status",
			"company",
			"custom_employee_work_agreement",
			"custom_statutory_coverage_profile",
		],
		as_dict=True,
	)
	if not row or row.company != company:
		frappe.throw(_("Employee {0} does not belong to {1}.").format(employee, company))
	if not row.custom_employee_work_agreement or not row.custom_statutory_coverage_profile:
		frappe.throw(_("Employee {0} is missing a work agreement or coverage profile.").format(employee))
	agreement = frappe.get_doc("Employee Work Agreement", row.custom_employee_work_agreement)
	validate_work_agreement_scope(agreement)
	profile = frappe.db.get_value(
		"Malaysia Employee Profile",
		{"employee": employee},
		["nationality_status", "tax_regime"],
		as_dict=True,
	)
	if not profile or profile.nationality_status not in allowed_nationalities(company):
		frappe.throw(_("Employee {0} is outside the supported citizenship policy.").format(employee))
	if profile.tax_regime != "STANDARD":
		frappe.throw(_("Employee {0} uses an unsupported PCB tax regime.").format(employee))


def _payroll_employee_names(doc) -> list[str]:
	return sorted({row.employee for row in getattr(doc, "employees", []) if getattr(row, "employee", None)})


def validate_payroll_entry_scope(doc, method=None) -> None:
	if not malaysia_payroll_enabled(getattr(doc, "company", None)):
		return
	doc.custom_malaysia_enabled = 1
	company = frappe.db.get_value(
		"Company",
		doc.company,
		["custom_malaysia_jurisdiction", "custom_malaysia_citizenship_policy"],
		as_dict=True,
	)
	if not company or company.custom_malaysia_jurisdiction != SUPPORTED_JURISDICTION:
		frappe.throw(_("The Company must be configured for Peninsular Malaysia before payroll."))
	assert_rule_review_current(doc.company, doc.end_date)
	if getattr(doc, "custom_malaysia_final_run", 0):
		month = get_first_day(doc.end_date)
		doc.custom_malaysia_final_period_key = f"{doc.company}|{month}"
	else:
		doc.custom_malaysia_final_period_key = None

	errors = []
	for employee in _payroll_employee_names(doc):
		row = frappe.db.get_value(
			"Employee",
			employee,
			["status", "company", "custom_employee_work_agreement"],
			as_dict=True,
		)
		if not row or row.status != "Active" or row.company != doc.company:
			errors.append(f"{employee}: Employee is not active in {doc.company}.")
			continue
		if not row.custom_employee_work_agreement:
			errors.append(f"{employee}: Employee Work Agreement is missing.")
		else:
			agreement = frappe.get_doc("Employee Work Agreement", row.custom_employee_work_agreement)
			if agreement.jurisdiction != SUPPORTED_JURISDICTION or agreement.work_arrangement not in SUPPORTED_ARRANGEMENTS:
				errors.append(f"{employee}: unsupported agreement jurisdiction or work arrangement.")
		profile = frappe.db.get_value(
			"Malaysia Employee Profile",
			{"employee": employee},
			["nationality_status", "tax_regime"],
			as_dict=True,
		)
		if not profile:
			errors.append(f"{employee}: Malaysia Employee Profile is missing.")
		elif profile.nationality_status not in allowed_nationalities(doc.company):
			errors.append(f"{employee}: unsupported citizenship status {profile.nationality_status}.")
		elif profile.tax_regime != "STANDARD":
			errors.append(f"{employee}: unsupported PCB tax regime {profile.tax_regime}.")

	if errors:
		doc.custom_malaysia_validation_errors = json.dumps({"errors": errors, "warnings": []}, indent=2)
		doc.custom_malaysia_control_state = "Validation Failed"
	if errors:
		frappe.throw(_("Malaysia payroll validation failed:\n{0}").format("\n".join(errors[:50])))


def payroll_source_hash(payroll_entry: str) -> str:
	rows = frappe.get_all(
		"Salary Slip",
		filters={"payroll_entry": payroll_entry, "docstatus": 1},
		fields=["name", "employee", "net_pay", "custom_malaysia_statutory_snapshot"],
		order_by="employee, name",
		limit=100000,
	)
	employee_names = sorted({row.employee for row in rows})
	employees = (
		{
			row.name: row
			for row in frappe.get_all(
				"Employee",
				filters={"name": ["in", employee_names]},
				fields=["name", "employee_name", "bank_ac_no"],
				limit=100000,
			)
		}
		if employee_names
		else {}
	)
	payload = [
		{
			"name": row.name,
			"employee": row.employee,
			"employee_name": getattr(employees.get(row.employee), "employee_name", "") or "",
			"bank_account": getattr(employees.get(row.employee), "bank_ac_no", "") or "",
			"net_pay": str(row.net_pay or 0),
			"statutory_snapshot": row.custom_malaysia_statutory_snapshot or "",
		}
		for row in rows
	]
	return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def assert_company_activation(company: str) -> None:
	row = frappe.db.get_value(
		"Company",
		company,
		[
			"custom_malaysia_production_activated",
			"custom_malaysia_jurisdiction",
			"custom_malaysia_citizenship_policy",
			"custom_malaysia_activation_evidence",
			"custom_malaysia_privacy_notice",
			"custom_malaysia_privacy_notice_version",
			"custom_malaysia_bank_file_format",
			"custom_malaysia_bank_uat_evidence",
			"custom_malaysia_last_backup_on",
			"custom_malaysia_backup_encrypted",
			"custom_malaysia_backup_evidence",
			"custom_hrd_corp_registered",
			"custom_hrd_corp_registration_number",
			"custom_hrd_levy_rate",
			"custom_malaysia_rule_review_deadline",
			"custom_malaysia_activated_by",
			"custom_malaysia_activation_hash",
			"custom_malaysia_last_restore_test",
		],
		as_dict=True,
	)
	if not row or not row.custom_malaysia_production_activated:
		frappe.throw(_("Malaysia production controls are not activated for this Company."))
	assert_rule_review_current(company, getdate())
	account_snapshot = assert_payroll_accounts_configured(company)
	if row.custom_malaysia_jurisdiction != SUPPORTED_JURISDICTION:
		frappe.throw(_("Only Peninsular Malaysia may be activated in this release."))
	if row.custom_malaysia_citizenship_policy not in {
		"Malaysian Citizens Only",
		"Malaysian Citizens and Permanent Residents",
	}:
		frappe.throw(_("The configured citizenship policy is not supported."))
	if not row.custom_malaysia_activation_evidence:
		frappe.throw(_("Production activation evidence is missing."))
	if not row.custom_malaysia_privacy_notice or not row.custom_malaysia_privacy_notice_version:
		frappe.throw(_("A versioned Malaysia employee privacy notice is required for production release."))
	if not row.custom_hrd_corp_registered or not row.custom_hrd_corp_registration_number:
		frappe.throw(_("HRD Corp registration is required for the configured 10+ employee deployment."))
	if Decimal(str(row.custom_hrd_levy_rate or 0)) != Decimal("1"):
		frappe.throw(_("The configured 10+ employee deployment requires the reviewed 1% HRD Corp levy rate."))
	if row.custom_malaysia_bank_file_format in {None, "", "Not Configured", "Generic CSV (UAT Only)"}:
		frappe.throw(_("A bank-specific, UAT-approved payroll file adapter is required for production release."))
	from malaysia_workforce.banking.service import production_bank_adapter_available

	if not production_bank_adapter_available(row.custom_malaysia_bank_file_format):
		frappe.throw(_("The configured production bank adapter is not installed."))
	if not row.custom_malaysia_bank_uat_evidence:
		frappe.throw(_("Bank file UAT evidence is missing."))
	if (
		not row.custom_malaysia_last_backup_on
		or get_datetime(row.custom_malaysia_last_backup_on) < add_to_date(now_datetime(), hours=-24)
		or not row.custom_malaysia_backup_encrypted
		or not row.custom_malaysia_backup_evidence
	):
		frappe.throw(_("A verified encrypted backup from the last 24 hours is required before payroll release."))
	if (
		not row.custom_malaysia_last_restore_test
		or getdate(row.custom_malaysia_last_restore_test) < getdate(add_days(getdate(), -90))
	):
		frappe.throw(_("A successful backup restoration test from the last 90 days is required before release."))
	if not row.custom_malaysia_rule_review_deadline or getdate(row.custom_malaysia_rule_review_deadline) < getdate():
		frappe.throw(_("The Company statutory rule review deadline has expired."))
	payload = {
		"company": company,
		"checks": {
			"jurisdiction": True,
			"citizenship_policy": True,
			"activation_evidence": True,
			"privacy_notice": True,
			"privacy_acknowledgements": True,
			"hrd_registration": True,
			"hrd_rate_1_percent": True,
			"bank_uat_evidence": True,
			"bank_adapter_installed": True,
			"backup_current_and_encrypted": True,
			"restore_test_recorded": True,
			"rule_review_deadline_valid": bool(
				row.custom_malaysia_rule_review_deadline
				and getdate(row.custom_malaysia_rule_review_deadline) >= getdate()
			),
			"accounts_configured": True,
		},
		"jurisdiction": row.custom_malaysia_jurisdiction,
		"citizenship_policy": row.custom_malaysia_citizenship_policy,
		"activation_evidence": row.custom_malaysia_activation_evidence,
		"privacy_notice": row.custom_malaysia_privacy_notice,
		"privacy_notice_version": row.custom_malaysia_privacy_notice_version,
		"hrd_registration_number": row.custom_hrd_corp_registration_number,
		"hrd_rate": str(row.custom_hrd_levy_rate or 0),
		"bank_uat_evidence": row.custom_malaysia_bank_uat_evidence,
		"bank_adapter": row.custom_malaysia_bank_file_format,
		"restore_test": str(row.custom_malaysia_last_restore_test),
		"rule_review_deadline": str(row.custom_malaysia_rule_review_deadline),
		"activated_by": row.custom_malaysia_activated_by,
		"account_snapshot": account_snapshot,
	}
	expected_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
	if row.custom_malaysia_activation_hash != expected_hash:
		frappe.throw(_("Production activation inputs changed after sign-off. Run the activation checklist again."))
