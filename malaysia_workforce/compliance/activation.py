from __future__ import annotations

import hashlib
import json
from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import add_days, add_to_date, get_datetime, getdate, now_datetime

from malaysia_workforce.banking.service import production_bank_adapter_available
from malaysia_workforce.compliance.scope import assert_payroll_accounts_configured
from malaysia_workforce.utils import ensure_private_file, ensure_roles


@frappe.whitelist(methods=["POST"])
def activate_company(company: str) -> dict:
	"""Record human activation after the deployer has completed external UAT."""
	ensure_roles("HR Manager", "Malaysia HR Manager", "System Manager")
	doc = frappe.get_doc("Company", company)
	doc.check_permission("write")
	for value, label in (
		(doc.custom_malaysia_activation_evidence, _("Production activation evidence")),
		(doc.custom_malaysia_bank_uat_evidence, _("Bank UAT evidence")),
		(doc.custom_malaysia_backup_evidence, _("Backup evidence")),
	):
		ensure_private_file(value, label)
	privacy_notice_version = (doc.custom_malaysia_privacy_notice_version or "").strip()
	privacy_rows = frappe.get_all(
		"Employee",
		filters={"company": doc.name, "status": "Active"},
		fields=[
			"name",
			"custom_malaysia_privacy_acknowledgement",
			"custom_malaysia_privacy_notice_version",
		],
		limit=100000,
	)
	missing_privacy_acknowledgements = [
		row.name
		for row in privacy_rows
		if not row.custom_malaysia_privacy_acknowledgement
		or row.custom_malaysia_privacy_notice_version != privacy_notice_version
	]
	account_snapshot = assert_payroll_accounts_configured(doc.name)
	checks = {
		"jurisdiction": doc.custom_malaysia_jurisdiction == "Peninsular Malaysia",
		"citizenship_policy": doc.custom_malaysia_citizenship_policy
		in {"Malaysian Citizens Only", "Malaysian Citizens and Permanent Residents"},
		"activation_evidence": bool(doc.custom_malaysia_activation_evidence),
		"privacy_notice": bool(doc.custom_malaysia_privacy_notice and privacy_notice_version),
		"privacy_acknowledgements": not missing_privacy_acknowledgements,
		"hrd_registration": bool(doc.custom_hrd_corp_registered and doc.custom_hrd_corp_registration_number),
		"hrd_rate_1_percent": Decimal(str(doc.custom_hrd_levy_rate or 0)) == Decimal("1"),
		"bank_uat_evidence": bool(doc.custom_malaysia_bank_uat_evidence),
		"bank_adapter_installed": production_bank_adapter_available(doc.custom_malaysia_bank_file_format),
		"backup_current_and_encrypted": bool(
			doc.custom_malaysia_last_backup_on
			and get_datetime(doc.custom_malaysia_last_backup_on)
			>= add_to_date(now_datetime(), hours=-24)
			and doc.custom_malaysia_backup_encrypted
			and doc.custom_malaysia_backup_evidence
		),
		"restore_test_recorded": bool(
			doc.custom_malaysia_last_restore_test
			and getdate(doc.custom_malaysia_last_restore_test) >= getdate(add_days(getdate(), -90))
		),
		"rule_review_deadline_valid": bool(
			doc.custom_malaysia_rule_review_deadline
			and getdate(doc.custom_malaysia_rule_review_deadline) >= getdate()
		),
		"accounts_configured": True,
	}
	failed = [key for key, passed in checks.items() if not passed]
	if failed:
		frappe.throw(_("Production activation checklist is incomplete: {0}.").format(", ".join(failed)))
	payload = {
		"company": doc.name,
		"checks": checks,
		"jurisdiction": doc.custom_malaysia_jurisdiction,
		"citizenship_policy": doc.custom_malaysia_citizenship_policy,
		"activation_evidence": doc.custom_malaysia_activation_evidence,
		"privacy_notice": doc.custom_malaysia_privacy_notice,
		"privacy_notice_version": privacy_notice_version,
		"hrd_registration_number": doc.custom_hrd_corp_registration_number,
		"hrd_rate": str(doc.custom_hrd_levy_rate or 0),
		"bank_uat_evidence": doc.custom_malaysia_bank_uat_evidence,
		"bank_adapter": doc.custom_malaysia_bank_file_format,
		"restore_test": str(doc.custom_malaysia_last_restore_test),
		"rule_review_deadline": str(doc.custom_malaysia_rule_review_deadline),
		"activated_by": frappe.session.user,
		"account_snapshot": account_snapshot,
	}
	digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
	frappe.db.set_value(
		"Company",
		doc.name,
		{
			"custom_malaysia_production_activated": 1,
			"custom_malaysia_activated_by": frappe.session.user,
			"custom_malaysia_activated_on": now_datetime(),
			"custom_malaysia_activation_hash": digest,
		},
		update_modified=True,
	)
	return {"company": doc.name, "activated": True, "activation_sha256": digest}


@frappe.whitelist(methods=["POST"])
def deactivate_company(company: str, reason: str) -> dict:
	ensure_roles("HR Manager", "Malaysia HR Manager", "System Manager")
	if not reason or not str(reason).strip():
		frappe.throw(_("A deactivation reason is required."))
	doc = frappe.get_doc("Company", company)
	doc.check_permission("write")
	doc.add_comment("Comment", text=f"Malaysia production controls deactivated by {frappe.session.user}: {str(reason).strip()}")
	frappe.db.set_value("Company", company, "custom_malaysia_production_activated", 0, update_modified=True)
	return {"company": company, "activated": False}
