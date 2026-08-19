from __future__ import annotations

import frappe

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields as _create_custom_fields
from malaysia_workforce.payroll.profile import STANDARD_PAYROLL_PROFILE, STATUTORY_PROFILE_OPTIONS


STANDARD_PROFILE_DEPENDS_ON = (
	"eval:!doc.custom_malaysia_statutory_profile "
	f"|| doc.custom_malaysia_statutory_profile=='{STANDARD_PAYROLL_PROFILE}'"
)


LEGACY_CUSTOM_FIELDS = {
	"Additional Salary": {"custom_malaysia_source_key", "custom_malaysia_workforce_section",
		"custom_generated_by_malaysia_workforce", "custom_source_batch_key", "custom_pay_calculation_version"},
	"Company": {"custom_malaysia_citizenship_policy", "custom_malaysia_production_activated",
		"custom_malaysia_privacy_notice", "custom_malaysia_privacy_notice_version", "custom_hrd_corp_registered",
		"custom_malaysia_activated_by", "custom_hrd_corp_registration_number", "custom_hrd_levy_rate",
		"custom_malaysia_activated_on", "custom_malaysia_activation_hash", "custom_malaysia_rule_review_deadline",
		"custom_malaysia_bank_file_format", "custom_malaysia_bank_uat_evidence", "custom_malaysia_last_backup_on",
		"custom_malaysia_backup_encrypted", "custom_malaysia_backup_evidence", "custom_malaysia_last_restore_test",
		"custom_malaysia_payroll_section", "custom_lhdn_employer_tin", "custom_malaysia_rule_pack",
		"custom_malaysia_rules_reviewed_through", "custom_malaysia_payroll_activated",
		"custom_malaysia_activation_evidence"},
	"Employee": {"custom_malaysia_workforce_section", "custom_employee_work_agreement",
		"custom_malaysia_employee_profile", "custom_statutory_coverage_profile", "custom_staffing_priority",
		"custom_staffing_priority_reason", "custom_staffing_priority_effective_from",
		"custom_staffing_priority_reviewed_by", "custom_staffing_priority_reviewed_on",
		"custom_staffing_priority_expires_on", "custom_other_employment_declared",
		"custom_malaysia_privacy_acknowledgement", "custom_malaysia_privacy_notice_version",
		"custom_malaysia_privacy_acknowledged_by", "custom_malaysia_privacy_acknowledged_on",
		"custom_kiosk_credential_hash", "custom_monthly_zakat", "custom_malaysia_statutory_section",
		"custom_malaysia_payroll_employee", "custom_malaysia_effective_from", "custom_socso_member_number"},
	"Employee Checkin": {"custom_malaysia_checkin_section", "custom_shift_work_record", "custom_checkin_method",
		"custom_kiosk_event_id", "custom_kiosk_id", "custom_device_timestamp", "custom_server_received_timestamp",
		"custom_kiosk_clock_drift_seconds", "custom_kiosk_event_hash", "custom_malaysia_correction_pair_id",
		"custom_malaysia_correction_status", "custom_malaysia_correction_explanation",
		"custom_malaysia_correction_requested_by", "custom_malaysia_correction_requested_on",
		"custom_malaysia_correction_reviewed_by", "custom_malaysia_correction_reviewed_on",
		"custom_malaysia_correction_evidence"},
	"Issue": {"custom_malaysia_incident_section", "custom_malaysia_workplace_incident",
		"custom_incident_company", "custom_incident_employee", "custom_incident_occurred_on",
		"custom_perkeso_escalation_due", "custom_dosh_reporting_required", "custom_incident_report_evidence"},
	"Journal Entry": {"custom_malaysia_payroll_entry", "custom_malaysia_journal_key"},
	"Payroll Entry": {"custom_malaysia_controls_section", "custom_malaysia_enabled", "custom_malaysia_final_run",
		"custom_malaysia_final_period_key", "custom_malaysia_control_state", "custom_malaysia_source_snapshot_hash",
		"custom_malaysia_work_record_reservation_status", "custom_malaysia_validation_errors",
		"custom_malaysia_processed_by", "custom_malaysia_released_on", "custom_malaysia_filing_status",
		"custom_malaysia_employer_contribution_journal", "custom_malaysia_employer_contribution_total",
		"custom_malaysia_bank_file", "custom_malaysia_bank_file_hash", "custom_malaysia_bank_reconciliation_state",
		"custom_malaysia_bank_reference", "custom_malaysia_bank_paid_count", "custom_malaysia_bank_paid_total",
		"custom_malaysia_bank_difference", "custom_malaysia_bank_evidence",
		"custom_malaysia_statutory_preparation_status", "custom_malaysia_payroll_section",
		"custom_malaysia_readiness_status", "custom_malaysia_release_status",
		"custom_malaysia_audit_section", "custom_malaysia_rule_pack", "custom_malaysia_source_hash",
		"custom_malaysia_released_by", "custom_malaysia_released_at"},
	"Salary Component": {"custom_malaysia_component", "custom_include_in_pcb_remuneration",
		"custom_pcb_remuneration_type", "custom_include_in_lindung_wages", "custom_malaysia_deduction_basis",
		"custom_malaysia_deduction_authority"},
	"Salary Slip": {"custom_malaysia_statutory_tab", "custom_malaysia_statutory_snapshot",
		"custom_malaysia_payroll_entry", "custom_statutory_recalculation_required", "custom_statutory_locked",
		"custom_malaysia_final_pay_type", "custom_malaysia_deduction_evidence", "custom_malaysia_source_hash"},
	"Shift Assignment": {"custom_malaysia_staffing_section", "custom_malaysia_staffing_plan",
		"custom_malaysia_staffing_recommendation_key", "custom_malaysia_assigned_designation",
		"custom_malaysia_rate_snapshot", "custom_malaysia_source_hash", "custom_shift_work_record"},
	"Shift Type": {"custom_malaysia_managed_shift", "custom_malaysia_shift_template",
		"custom_malaysia_shift_fingerprint"},
	"ToDo": {"custom_malaysia_exception_code", "custom_malaysia_content_hash",
		"custom_malaysia_resolution_evidence", "custom_malaysia_resolved_by",
		"custom_malaysia_resolved_on", "custom_malaysia_resolution_hash"},
	"Training Event": {"custom_hrd_corp_section", "custom_hrd_corp_submission",
		"custom_hrd_corp_grant_evidence"},
}


def create_custom_fields(only_doctypes: set[str] | None = None):
	"""Install the minimum fields needed to localise standard payroll records."""
	fields = {
		"Company": [
			{"fieldname": "custom_malaysia_payroll_tab", "label": "Statutory Payroll", "fieldtype": "Tab Break", "insert_after": "default_payroll_payable_account"},
			{"fieldname": "custom_enable_malaysia_payroll", "label": "Enable Statutory Payroll", "fieldtype": "Check", "default": "0", "insert_after": "custom_malaysia_payroll_tab"},
			{"fieldname": "custom_malaysia_jurisdiction", "label": "Payroll Jurisdiction", "fieldtype": "Select", "options": "Peninsular Malaysia", "default": "Peninsular Malaysia", "insert_after": "custom_enable_malaysia_payroll", "mandatory_depends_on": "eval:doc.custom_enable_malaysia_payroll"},
			{"fieldname": "custom_company_registration_number", "label": "SSM Registration Number", "fieldtype": "Data", "insert_after": "custom_malaysia_jurisdiction"},
			{"fieldname": "custom_lhdn_hq_number", "label": "LHDN HQ Number", "fieldtype": "Data", "insert_after": "custom_company_registration_number"},
			{"fieldname": "custom_lhdn_employer_number", "label": "LHDN Employer Number", "fieldtype": "Data", "insert_after": "custom_lhdn_hq_number"},
			{"fieldname": "custom_epf_employer_number", "label": "EPF Employer Number", "fieldtype": "Data", "insert_after": "custom_lhdn_employer_number"},
			{"fieldname": "custom_socso_employer_code", "label": "PERKESO Employer Code", "fieldtype": "Data", "insert_after": "custom_epf_employer_number"},
			{"fieldname": "custom_hrd_registration_class", "label": "HRD Corp Registration", "fieldtype": "Select", "options": "\nNot Registered\nOptional (0.5%)\nCompulsory (1%)", "insert_after": "custom_socso_employer_code"},
			{"fieldname": "custom_hrd_registration_number", "label": "HRD Corp Registration Number", "fieldtype": "Data", "insert_after": "custom_hrd_registration_class"},
			{"fieldname": "custom_hrd_effective_from", "label": "HRD Corp Effective From", "fieldtype": "Date", "insert_after": "custom_hrd_registration_number"},
		],
		"Employee": [
			{"fieldname": "custom_malaysia_payroll_tab", "label": "Statutory Details", "fieldtype": "Tab Break", "insert_after": "personal_details", "permlevel": 1},
			{"fieldname": "custom_malaysia_citizenship_status", "label": "Citizenship Status", "fieldtype": "Select", "options": "\nMalaysian Citizen\nPermanent Resident", "insert_after": "custom_malaysia_payroll_tab", "permlevel": 1},
			{"fieldname": "custom_malaysia_statutory_profile", "label": "Statutory Profile", "fieldtype": "Select", "options": STATUTORY_PROFILE_OPTIONS, "default": STANDARD_PAYROLL_PROFILE, "insert_after": "custom_malaysia_citizenship_status", "permlevel": 1, "description": "Choose Standard Payroll for ordinary employees. Choose SOCSO + EIS — LINDUNG Optional when only these contributions are handled in payroll."},
			{"fieldname": "custom_nric", "label": "NRIC", "fieldtype": "Data", "insert_after": "custom_malaysia_statutory_profile", "permlevel": 1},
			{"fieldname": "custom_tax_identification_number", "label": "Tax Identification Number", "fieldtype": "Data", "insert_after": "custom_nric", "permlevel": 1, "depends_on": STANDARD_PROFILE_DEPENDS_ON},
			{"fieldname": "custom_epf_member_number", "label": "EPF Member Number", "fieldtype": "Data", "insert_after": "custom_tax_identification_number", "permlevel": 1, "depends_on": STANDARD_PROFILE_DEPENDS_ON},
			{"fieldname": "custom_socso_category", "label": "SOCSO Category", "fieldtype": "Select", "options": "First\nSecond", "default": "First", "insert_after": "custom_epf_member_number", "permlevel": 1, "read_only": 1, "description": "Auto-derived from Date of Birth: First Category (invalidity + employment injury) under age 60, Second Category (employment injury only) from age 60."},
			{"fieldname": "custom_eis_eligible", "label": "EIS Eligible", "fieldtype": "Check", "default": "1", "insert_after": "custom_socso_category", "permlevel": 1, "read_only": 1, "description": "Auto-derived from Date of Birth: EIS applies from age 18 up to age 60."},
			{"fieldname": "custom_lindung_participation", "label": "LINDUNG 24 Jam Participation", "fieldtype": "Select", "options": "Participating\nNot Participating", "default": "Participating", "insert_after": "custom_eis_eligible", "permlevel": 1, "description": "Participation is the statutory default from 1 June 2026. Select Not Participating only after the employee has personally filed a PERKESO Liability Release Notice."},
			{"fieldname": "custom_lindung_registration_date", "label": "PERKESO Registration Date", "fieldtype": "Date", "insert_after": "custom_lindung_participation", "depends_on": "eval:doc.custom_lindung_participation=='Not Participating'", "mandatory_depends_on": "eval:doc.custom_lindung_participation=='Not Participating'", "permlevel": 1, "description": "Required only to validate the official liability-release window."},
			{"fieldname": "custom_lindung_effective_from", "label": "Liability Release Effective From", "fieldtype": "Date", "insert_after": "custom_lindung_registration_date", "depends_on": "eval:doc.custom_lindung_participation=='Not Participating'", "mandatory_depends_on": "eval:doc.custom_lindung_participation=='Not Participating'", "permlevel": 1, "description": "Date the employee's PERKESO Liability Release Notice takes effect. Contributions continue for every month ending before this date."},
			{"fieldname": "custom_lindung_evidence", "label": "Liability Release Notice", "fieldtype": "Attach", "insert_after": "custom_lindung_effective_from", "depends_on": "eval:doc.custom_lindung_participation=='Not Participating'", "permlevel": 1, "description": "The employee's own Notis/Perakuan Pelepasan Liabiliti from the LINDUNG Faedah portal. The employer may not file it on the employee's behalf."},
			{"fieldname": "custom_lindung_multiple_employers", "label": "Has Multiple Employers", "fieldtype": "Check", "default": "0", "insert_after": "custom_lindung_evidence", "permlevel": 1, "description": "LINDUNG must be deducted by only PERKESO's selected employer. Phase 1 payroll stops for this case rather than guessing."},
			{"fieldname": "custom_pcb_resident", "label": "Resident for PCB", "fieldtype": "Check", "default": "1", "insert_after": "custom_lindung_multiple_employers", "permlevel": 1, "depends_on": STANDARD_PROFILE_DEPENDS_ON},
			{"fieldname": "custom_pcb_category", "label": "PCB Category", "fieldtype": "Select", "options": "1 - Single\n2 - Married, spouse not working\n3 - Married, spouse working", "default": "1 - Single", "insert_after": "custom_pcb_resident", "permlevel": 1, "depends_on": STANDARD_PROFILE_DEPENDS_ON, "description": "LHDN monthly tax category for this employee."},
			{"fieldname": "custom_pcb_child_units", "label": "PCB Child Relief Units", "fieldtype": "Float", "default": "0", "insert_after": "custom_pcb_category", "permlevel": 1, "depends_on": STANDARD_PROFILE_DEPENDS_ON},
			{"fieldname": "custom_pcb_individual_disabled", "label": "Individual Disabled", "fieldtype": "Check", "default": "0", "insert_after": "custom_pcb_child_units", "permlevel": 1, "depends_on": STANDARD_PROFILE_DEPENDS_ON},
			{"fieldname": "custom_pcb_spouse_disabled", "label": "Spouse Disabled", "fieldtype": "Check", "default": "0", "insert_after": "custom_pcb_individual_disabled", "permlevel": 1, "depends_on": STANDARD_PROFILE_DEPENDS_ON},
		],
		"Contract": [
			{"fieldname": "custom_malaysia_terms_section", "label": "Statutory Working Terms", "fieldtype": "Section Break", "insert_after": "contract_terms", "collapsible": 1},
			{"fieldname": "custom_malaysia_wage_basis", "label": "Wage Basis", "fieldtype": "Select", "options": "\nMonthly\nDaily\nHourly", "insert_after": "custom_malaysia_terms_section"},
			{"fieldname": "custom_malaysia_work_classification", "label": "Work Classification", "fieldtype": "Select", "options": "\nFull-time\nPart-time", "insert_after": "custom_malaysia_wage_basis"},
			{"fieldname": "custom_contract_wage_rate", "label": "Daily or Hourly Rate", "fieldtype": "Currency", "insert_after": "custom_malaysia_work_classification", "depends_on": "eval:['Daily','Hourly'].includes(doc.custom_malaysia_wage_basis)", "mandatory_depends_on": "eval:['Daily','Hourly'].includes(doc.custom_malaysia_wage_basis)", "description": "Required only for daily or hourly employees. Salary Structure Assignment is authoritative for monthly wages."},
			{"fieldname": "custom_normal_hours_per_day", "label": "Normal Hours per Day", "fieldtype": "Float", "insert_after": "custom_contract_wage_rate"},
			{"fieldname": "custom_normal_hours_per_week", "label": "Normal Hours per Week", "fieldtype": "Float", "insert_after": "custom_normal_hours_per_day"},
			{"fieldname": "custom_comparable_full_time_hours_per_day", "label": "Comparable Full-time Hours per Day", "fieldtype": "Float", "insert_after": "custom_normal_hours_per_week", "depends_on": "eval:doc.custom_malaysia_work_classification=='Part-time'"},
			{"fieldname": "custom_comparable_full_time_hours", "label": "Comparable Full-time Hours per Week", "fieldtype": "Float", "insert_after": "custom_comparable_full_time_hours_per_day", "depends_on": "eval:doc.custom_malaysia_work_classification=='Part-time'"},
			{"fieldname": "custom_rest_day", "label": "Rest Day", "fieldtype": "Select", "options": "\nMonday\nTuesday\nWednesday\nThursday\nFriday\nSaturday\nSunday", "insert_after": "custom_comparable_full_time_hours"},
			{"fieldname": "custom_overtime_eligible", "label": "Overtime Eligible", "fieldtype": "Check", "default": "1", "insert_after": "custom_rest_day"},
		],
		"Salary Component": [
			{"fieldname": "custom_malaysia_statutory_section", "label": "Statutory Treatment", "fieldtype": "Section Break", "insert_after": "description", "collapsible": 1},
			{"fieldname": "custom_include_in_epf_wages", "label": "Include in EPF Wages", "fieldtype": "Check", "default": "0", "insert_after": "custom_malaysia_statutory_section"},
			{"fieldname": "custom_include_in_socso_wages", "label": "Include in SOCSO Wages", "fieldtype": "Check", "default": "0", "insert_after": "custom_include_in_epf_wages"},
			{"fieldname": "custom_include_in_eis_wages", "label": "Include in EIS Wages", "fieldtype": "Check", "default": "0", "insert_after": "custom_include_in_socso_wages"},
			{"fieldname": "custom_include_in_hrd_levy_wages", "label": "Include in HRD Levy Wages", "fieldtype": "Check", "default": "0", "insert_after": "custom_include_in_eis_wages"},
			{"fieldname": "custom_pcb_treatment", "label": "PCB Treatment", "fieldtype": "Select", "options": "\nNot Taxable\nRegular Remuneration\nAdditional Remuneration", "insert_after": "custom_include_in_hrd_levy_wages", "description": "This is the Malaysian PCB classification used in payroll. The HRMS “Is Tax Applicable” checkbox above does not drive PCB."},
			{"fieldname": "custom_include_in_ordinary_rate", "label": "Include in Ordinary Rate of Pay", "fieldtype": "Check", "default": "0", "insert_after": "custom_pcb_treatment"},
		],
		"Salary Slip": [
			{"fieldname": "custom_malaysia_results_tab", "label": "Statutory", "fieldtype": "Tab Break", "insert_after": "deductions"},
			{"fieldname": "custom_malaysia_payroll_section", "label": "Statutory Contributions", "fieldtype": "Section Break", "insert_after": "custom_malaysia_results_tab"},
			{"fieldname": "custom_malaysia_statutory_profile", "label": "Statutory Profile", "fieldtype": "Data", "read_only": 1, "permlevel": 1, "insert_after": "custom_malaysia_payroll_section"},
			{"fieldname": "custom_malaysia_statutory_results", "label": "Statutory Results", "fieldtype": "Table", "options": "Malaysia Statutory Result", "read_only": 1, "insert_after": "custom_malaysia_statutory_profile"},
			{"fieldname": "custom_malaysia_audit_section", "label": "Calculation Details", "fieldtype": "Section Break", "collapsible": 1, "collapsed": 1, "insert_after": "custom_malaysia_statutory_results"},
			{"fieldname": "custom_malaysia_rule_pack", "label": "Rule Pack", "fieldtype": "Data", "read_only": 1, "insert_after": "custom_malaysia_audit_section"},
		],
		"Overtime Type": [
			{"fieldname": "custom_malaysia_pay_type", "label": "Statutory Day Type", "fieldtype": "Select", "options": "\nNormal Overtime\nRest Day\nPublic Holiday", "insert_after": "overtime_salary_component", "description": "Malaysian overtime pay uses this day type. Do not use the HRMS public-holiday or weekend multiplier checkboxes for statutory overtime."},
		],
	}
	if only_doctypes:
		fields = {doctype: rows for doctype, rows in fields.items() if doctype in only_doctypes}
	_create_custom_fields(fields, update=True)
	if not only_doctypes or "Employee" in only_doctypes:
		_relabel_stored_pcb_categories()


def _relabel_stored_pcb_categories() -> None:
	"""Keep existing 1/2/3 codes selectable after the labelled options are installed."""
	if not frappe.db.has_column("Employee", "custom_pcb_category"):
		return
	mapping = {
		"1": "1 - Single",
		"2": "2 - Married, spouse not working",
		"3": "3 - Married, spouse working",
	}
	for old, new in mapping.items():
		frappe.db.sql(
			"update `tabEmployee` set custom_pcb_category = %s where custom_pcb_category = %s",
			(new, old),
		)


def remove_legacy_custom_fields() -> None:
	"""Remove only fields created by the abandoned pre-lean implementation."""
	for doctype, fieldnames in LEGACY_CUSTOM_FIELDS.items():
		for fieldname in sorted(fieldnames):
			name = f"{doctype}-{fieldname}"
			if frappe.db.exists("Custom Field", name):
				frappe.delete_doc("Custom Field", name, force=True, ignore_permissions=True)
	frappe.clear_cache()
