from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields as _create_custom_fields


def create_custom_fields(only_doctypes: set[str] | None = None):
	custom_fields = {
		"Employee": [
			{"fieldname": "custom_malaysia_workforce_section", "label": "Malaysia Workforce", "fieldtype": "Section Break", "insert_after": "employment_type", "collapsible": 1},
			{"fieldname": "custom_employee_work_agreement", "label": "Current Work Agreement", "fieldtype": "Link", "options": "Employee Work Agreement", "insert_after": "custom_malaysia_workforce_section", "read_only": 1},
			{"fieldname": "custom_malaysia_employee_profile", "label": "Malaysia Employee Profile", "fieldtype": "Link", "options": "Malaysia Employee Profile", "insert_after": "custom_employee_work_agreement", "read_only": 1},
			{"fieldname": "custom_statutory_coverage_profile", "label": "Statutory Coverage Profile", "fieldtype": "Link", "options": "Statutory Coverage Profile", "insert_after": "custom_malaysia_employee_profile", "read_only": 1},
			{"fieldname": "custom_staffing_priority", "label": "Staffing Priority", "fieldtype": "Select", "options": "Priority\nPreferred\nStandard", "default": "Standard", "insert_after": "custom_statutory_coverage_profile"},
			{"fieldname": "custom_staffing_priority_reason", "label": "Staffing Priority Reason", "fieldtype": "Small Text", "insert_after": "custom_staffing_priority", "mandatory_depends_on": "eval:doc.custom_staffing_priority && doc.custom_staffing_priority!='Standard'"},
			{"fieldname": "custom_staffing_priority_effective_from", "label": "Priority Effective From", "fieldtype": "Date", "insert_after": "custom_staffing_priority_reason", "mandatory_depends_on": "eval:doc.custom_staffing_priority && doc.custom_staffing_priority!='Standard'"},
			{"fieldname": "custom_staffing_priority_reviewed_by", "label": "Priority Reviewed By", "fieldtype": "Link", "options": "User", "insert_after": "custom_staffing_priority_effective_from", "read_only": 1, "no_copy": 1},
			{"fieldname": "custom_staffing_priority_reviewed_on", "label": "Priority Reviewed On", "fieldtype": "Datetime", "insert_after": "custom_staffing_priority_reviewed_by", "read_only": 1, "no_copy": 1},
			{"fieldname": "custom_staffing_priority_expires_on", "label": "Priority Expires On", "fieldtype": "Date", "insert_after": "custom_staffing_priority_reviewed_on", "mandatory_depends_on": "eval:doc.custom_staffing_priority && doc.custom_staffing_priority!='Standard'"},
			{"fieldname": "custom_other_employment_declared", "label": "Other Employment Declared", "fieldtype": "Check", "default": "0", "insert_after": "custom_staffing_priority_expires_on"},
			{"fieldname": "custom_malaysia_privacy_acknowledgement", "label": "Malaysia Privacy Notice Acknowledgement", "fieldtype": "Attach", "insert_after": "custom_other_employment_declared"},
			{"fieldname": "custom_malaysia_privacy_notice_version", "label": "Acknowledged Privacy Notice Version", "fieldtype": "Data", "insert_after": "custom_malaysia_privacy_acknowledgement", "read_only": 1},
			{"fieldname": "custom_malaysia_privacy_acknowledged_by", "label": "Privacy Notice Acknowledged By", "fieldtype": "Link", "options": "User", "insert_after": "custom_malaysia_privacy_notice_version", "read_only": 1, "no_copy": 1},
			{"fieldname": "custom_malaysia_privacy_acknowledged_on", "label": "Privacy Notice Acknowledged On", "fieldtype": "Datetime", "insert_after": "custom_malaysia_privacy_acknowledged_by", "read_only": 1, "no_copy": 1},
			{"fieldname": "custom_kiosk_credential_hash", "label": "Kiosk Credential Hash", "fieldtype": "Data", "insert_after": "custom_malaysia_privacy_acknowledged_on", "hidden": 1, "read_only": 1, "no_copy": 1},
		],
		"Company": [
			{"fieldname": "custom_malaysia_payroll_section", "label": "Malaysia Payroll", "fieldtype": "Section Break", "insert_after": "country", "collapsible": 1},
			{"fieldname": "custom_enable_malaysia_payroll", "label": "Enable Malaysia Payroll", "fieldtype": "Check", "default": "0", "insert_after": "custom_malaysia_payroll_section"},
			{"fieldname": "custom_malaysia_jurisdiction", "label": "Supported Jurisdiction", "fieldtype": "Select", "options": "Peninsular Malaysia", "default": "Peninsular Malaysia", "insert_after": "custom_enable_malaysia_payroll", "reqd": 1},
			{"fieldname": "custom_malaysia_citizenship_policy", "label": "Supported Citizenship", "fieldtype": "Select", "options": "Malaysian Citizens Only\nMalaysian Citizens and Permanent Residents", "default": "Malaysian Citizens Only", "insert_after": "custom_malaysia_jurisdiction", "reqd": 1},
			{"fieldname": "custom_malaysia_production_activated", "label": "Production Controls Activated", "fieldtype": "Check", "default": "0", "insert_after": "custom_malaysia_citizenship_policy", "read_only": 1},
			{"fieldname": "custom_malaysia_privacy_notice", "label": "Malaysia Employee Privacy Notice", "fieldtype": "Attach", "insert_after": "custom_malaysia_production_activated"},
			{"fieldname": "custom_malaysia_privacy_notice_version", "label": "Privacy Notice Version", "fieldtype": "Data", "insert_after": "custom_malaysia_privacy_notice"},
			{"fieldname": "custom_malaysia_activation_evidence", "label": "Production Activation Evidence", "fieldtype": "Attach", "insert_after": "custom_malaysia_privacy_notice_version"},
			{"fieldname": "custom_malaysia_activated_by", "label": "Activated By", "fieldtype": "Link", "options": "User", "insert_after": "custom_malaysia_activation_evidence", "read_only": 1},
			{"fieldname": "custom_malaysia_activated_on", "label": "Activated On", "fieldtype": "Datetime", "insert_after": "custom_malaysia_activated_by", "read_only": 1},
			{"fieldname": "custom_malaysia_activation_hash", "label": "Activation Checklist SHA-256", "fieldtype": "Data", "insert_after": "custom_malaysia_activated_on", "read_only": 1, "no_copy": 1},
			{"fieldname": "custom_lhdn_hq_number", "label": "LHDN HQ Number", "fieldtype": "Data", "insert_after": "custom_enable_malaysia_payroll"},
			{"fieldname": "custom_lhdn_employer_number", "label": "LHDN Employer Number", "fieldtype": "Data", "insert_after": "custom_lhdn_hq_number"},
			{"fieldname": "custom_epf_employer_number", "label": "EPF Employer Number", "fieldtype": "Data", "insert_after": "custom_lhdn_employer_number"},
			{"fieldname": "custom_socso_employer_code", "label": "SOCSO Employer Code", "fieldtype": "Data", "insert_after": "custom_epf_employer_number"},
			{"fieldname": "custom_company_registration_number", "label": "SSM / Company Registration Number", "fieldtype": "Data", "insert_after": "custom_socso_employer_code"},
			{"fieldname": "custom_hrd_corp_registered", "label": "Registered with HRD Corp", "fieldtype": "Check", "default": "0", "insert_after": "custom_company_registration_number"},
			{"fieldname": "custom_hrd_corp_registration_number", "label": "HRD Corp Registration Number", "fieldtype": "Data", "insert_after": "custom_hrd_corp_registered"},
			{"fieldname": "custom_hrd_levy_rate", "label": "HRD Corp Levy Rate (%)", "fieldtype": "Percent", "default": "1", "insert_after": "custom_hrd_corp_registration_number"},
			{"fieldname": "custom_malaysia_rule_review_deadline", "label": "Statutory Rule Review Deadline", "fieldtype": "Date", "insert_after": "custom_hrd_levy_rate"},
			{"fieldname": "custom_malaysia_bank_file_format", "label": "Payroll Bank Adapter Key", "fieldtype": "Data", "default": "Not Configured", "insert_after": "custom_malaysia_rule_review_deadline", "description": "Use Generic CSV (UAT Only) for shadow testing, or the exact key exposed by an installed bank-specific adapter app."},
			{"fieldname": "custom_malaysia_bank_uat_evidence", "label": "Bank UAT Evidence", "fieldtype": "Attach", "insert_after": "custom_malaysia_bank_file_format"},
			{"fieldname": "custom_malaysia_last_backup_on", "label": "Last Verified Backup On", "fieldtype": "Datetime", "insert_after": "custom_malaysia_bank_uat_evidence"},
			{"fieldname": "custom_malaysia_backup_encrypted", "label": "Backup Encryption Verified", "fieldtype": "Check", "default": "0", "insert_after": "custom_malaysia_last_backup_on"},
			{"fieldname": "custom_malaysia_backup_evidence", "label": "Backup Verification Evidence", "fieldtype": "Attach", "insert_after": "custom_malaysia_backup_encrypted"},
			{"fieldname": "custom_malaysia_last_restore_test", "label": "Last Successful Backup Restore Test", "fieldtype": "Date", "insert_after": "custom_malaysia_backup_evidence"},
		],
		"Salary Component": [
			{"fieldname": "custom_malaysia_statutory_section", "label": "Malaysia Statutory Classification", "fieldtype": "Section Break", "insert_after": "description", "collapsible": 1},
			{"fieldname": "custom_malaysia_component", "label": "Managed by Malaysia Workforce", "fieldtype": "Check", "default": "0", "insert_after": "custom_malaysia_statutory_section"},
			{"fieldname": "custom_include_in_epf_wages", "label": "Include in EPF Wages", "fieldtype": "Check", "default": "0", "insert_after": "custom_malaysia_component"},
			{"fieldname": "custom_include_in_socso_wages", "label": "Include in SOCSO Wages", "fieldtype": "Check", "default": "0", "insert_after": "custom_include_in_epf_wages"},
			{"fieldname": "custom_include_in_eis_wages", "label": "Include in EIS Wages", "fieldtype": "Check", "default": "0", "insert_after": "custom_include_in_socso_wages"},
			{"fieldname": "custom_include_in_pcb_remuneration", "label": "Include in PCB Remuneration", "fieldtype": "Check", "default": "0", "insert_after": "custom_include_in_eis_wages"},
			{"fieldname": "custom_pcb_remuneration_type", "label": "PCB Remuneration Type", "fieldtype": "Select", "options": "\nRegular Remuneration\nAdditional Remuneration\nBenefit in Kind\nPerquisite\nNot Applicable", "insert_after": "custom_include_in_pcb_remuneration"},
			{"fieldname": "custom_include_in_lindung_wages", "label": "Include in LINDUNG Wages", "fieldtype": "Check", "default": "0", "insert_after": "custom_pcb_remuneration_type"},
			{"fieldname": "custom_include_in_hrd_levy_wages", "label": "Include in HRD Corp Levy Wages", "fieldtype": "Check", "default": "0", "insert_after": "custom_include_in_lindung_wages"},
			{"fieldname": "custom_malaysia_deduction_basis", "label": "Malaysia Deduction Authority", "fieldtype": "Select", "options": "\nWritten Law\nEmployee Written Request\nEmployer Recovery\nFinal Employer Debt\nDG-Approved Housing Loan\nOther / Unclassified", "insert_after": "custom_include_in_hrd_levy_wages"},
		],
		"Shift Assignment": [
			{"fieldname": "custom_malaysia_staffing_section", "label": "Malaysia Staffing Source", "fieldtype": "Section Break", "insert_after": "shift_schedule_assignment", "collapsible": 1},
			{"fieldname": "custom_malaysia_staffing_plan", "label": "Staffing Plan", "fieldtype": "Link", "options": "Cafe Staffing Plan", "insert_after": "custom_malaysia_staffing_section", "read_only": 1, "search_index": 1},
			{"fieldname": "custom_malaysia_staffing_recommendation_key", "label": "Recommendation Key", "fieldtype": "Data", "insert_after": "custom_malaysia_staffing_plan", "read_only": 1, "unique": 1, "no_copy": 1},
			{"fieldname": "custom_malaysia_assigned_designation", "label": "Assigned Designation", "fieldtype": "Link", "options": "Designation", "insert_after": "custom_malaysia_staffing_recommendation_key", "read_only": 1},
			{"fieldname": "custom_malaysia_rate_snapshot", "label": "Hourly Rate Snapshot", "fieldtype": "Currency", "insert_after": "custom_malaysia_assigned_designation", "read_only": 1},
			{"fieldname": "custom_malaysia_source_hash", "label": "Staffing Source SHA-256", "fieldtype": "Data", "insert_after": "custom_malaysia_rate_snapshot", "read_only": 1, "no_copy": 1},
			{"fieldname": "custom_shift_work_record", "label": "Shift Work Record", "fieldtype": "Link", "options": "Shift Work Record", "insert_after": "custom_malaysia_source_hash", "read_only": 1},
		],
		"Shift Type": [
			{"fieldname": "custom_malaysia_managed_shift", "label": "Managed Flexible Shift", "fieldtype": "Check", "default": "0", "insert_after": "color", "read_only": 1},
			{"fieldname": "custom_malaysia_shift_template", "label": "Base Shift Type", "fieldtype": "Link", "options": "Shift Type", "insert_after": "custom_malaysia_managed_shift", "read_only": 1},
			{"fieldname": "custom_malaysia_shift_fingerprint", "label": "Flexible Shift Fingerprint", "fieldtype": "Data", "insert_after": "custom_malaysia_shift_template", "read_only": 1, "unique": 1, "no_copy": 1},
		],
		"Employee Checkin": [
			{"fieldname": "custom_malaysia_checkin_section", "label": "Malaysia Workforce", "fieldtype": "Section Break", "insert_after": "device_id", "collapsible": 1},
			{"fieldname": "custom_shift_work_record", "label": "Shift Work Record", "fieldtype": "Link", "options": "Shift Work Record", "insert_after": "custom_malaysia_checkin_section", "read_only": 1},
			{"fieldname": "custom_checkin_method", "label": "Check-in Method", "fieldtype": "Select", "options": "\nMobile\nQR\nKiosk\nBiometric\nManual\nIntegration", "insert_after": "custom_shift_work_record"},
			{"fieldname": "custom_kiosk_event_id", "label": "Kiosk Event ID", "fieldtype": "Data", "insert_after": "custom_checkin_method", "read_only": 1, "unique": 1, "no_copy": 1},
			{"fieldname": "custom_kiosk_id", "label": "Kiosk ID", "fieldtype": "Data", "insert_after": "custom_kiosk_event_id", "read_only": 1},
			{"fieldname": "custom_device_timestamp", "label": "Device Timestamp", "fieldtype": "Datetime", "insert_after": "custom_kiosk_id", "read_only": 1},
			{"fieldname": "custom_server_received_timestamp", "label": "Server Received Timestamp", "fieldtype": "Datetime", "insert_after": "custom_device_timestamp", "read_only": 1},
			{"fieldname": "custom_kiosk_clock_drift_seconds", "label": "Kiosk Clock Drift (Seconds)", "fieldtype": "Float", "insert_after": "custom_server_received_timestamp", "read_only": 1},
			{"fieldname": "custom_kiosk_event_hash", "label": "Kiosk Event SHA-256", "fieldtype": "Data", "insert_after": "custom_kiosk_clock_drift_seconds", "read_only": 1, "no_copy": 1},
			{"fieldname": "custom_malaysia_correction_pair_id", "label": "Attendance Correction Pair ID", "fieldtype": "Data", "insert_after": "custom_kiosk_event_hash", "read_only": 1, "search_index": 1, "no_copy": 1},
			{"fieldname": "custom_malaysia_correction_status", "label": "Attendance Correction Status", "fieldtype": "Select", "options": "\nPending Review\nApproved\nRejected", "insert_after": "custom_malaysia_correction_pair_id", "read_only": 1, "no_copy": 1},
			{"fieldname": "custom_malaysia_correction_explanation", "label": "Attendance Correction Explanation", "fieldtype": "Small Text", "insert_after": "custom_malaysia_correction_status", "read_only": 1, "no_copy": 1},
			{"fieldname": "custom_malaysia_correction_requested_by", "label": "Attendance Correction Requested By", "fieldtype": "Link", "options": "User", "insert_after": "custom_malaysia_correction_explanation", "read_only": 1, "no_copy": 1},
			{"fieldname": "custom_malaysia_correction_requested_on", "label": "Attendance Correction Requested On", "fieldtype": "Datetime", "insert_after": "custom_malaysia_correction_requested_by", "read_only": 1, "no_copy": 1},
			{"fieldname": "custom_malaysia_correction_reviewed_by", "label": "Attendance Correction Reviewed By", "fieldtype": "Link", "options": "User", "insert_after": "custom_malaysia_correction_requested_on", "read_only": 1, "no_copy": 1},
			{"fieldname": "custom_malaysia_correction_reviewed_on", "label": "Attendance Correction Reviewed On", "fieldtype": "Datetime", "insert_after": "custom_malaysia_correction_reviewed_by", "read_only": 1, "no_copy": 1},
			{"fieldname": "custom_malaysia_correction_evidence", "label": "Attendance Correction Evidence", "fieldtype": "Attach", "insert_after": "custom_malaysia_correction_reviewed_on", "read_only": 1, "no_copy": 1},
		],
		"Additional Salary": [
			{"fieldname": "custom_malaysia_workforce_section", "label": "Malaysia Workforce", "fieldtype": "Section Break", "insert_after": "ref_docname", "collapsible": 1},
			{"fieldname": "custom_generated_by_malaysia_workforce", "label": "Generated by Malaysia Workforce", "fieldtype": "Check", "default": "0", "insert_after": "custom_malaysia_workforce_section", "read_only": 1},
			{"fieldname": "custom_source_batch_key", "label": "Source Batch Key", "fieldtype": "Data", "insert_after": "custom_generated_by_malaysia_workforce", "read_only": 1, "search_index": 1},
			{"fieldname": "custom_pay_calculation_version", "label": "Pay Calculation Version", "fieldtype": "Data", "insert_after": "custom_source_batch_key", "read_only": 1},
		],
		"Salary Slip": [
			{"fieldname": "custom_malaysia_statutory_tab", "label": "Malaysia Statutory", "fieldtype": "Tab Break", "insert_after": "leave_details"},
			{"fieldname": "custom_malaysia_statutory_results", "label": "Statutory Results", "fieldtype": "Table", "options": "Malaysia Statutory Result", "insert_after": "custom_malaysia_statutory_tab", "read_only": 1},
			{"fieldname": "custom_malaysia_statutory_snapshot", "label": "Statutory Calculation Snapshot", "fieldtype": "Code", "options": "JSON", "insert_after": "custom_malaysia_statutory_results", "read_only": 1},
			{"fieldname": "custom_malaysia_payroll_entry", "label": "Malaysia Payroll Entry", "fieldtype": "Link", "options": "Payroll Entry", "insert_after": "custom_malaysia_statutory_snapshot", "read_only": 1},
			{"fieldname": "custom_statutory_recalculation_required", "label": "Statutory Recalculation Required", "fieldtype": "Check", "default": "0", "insert_after": "custom_malaysia_payroll_entry", "read_only": 1},
			{"fieldname": "custom_statutory_locked", "label": "Statutory Snapshot Locked", "fieldtype": "Check", "default": "0", "insert_after": "custom_statutory_recalculation_required", "read_only": 1},
			{"fieldname": "custom_malaysia_final_pay_type", "label": "Malaysia Final Pay Type", "fieldtype": "Select", "options": "\nNormal Termination or Notice\nEmployer Termination Without Notice\nEmployee Termination Without Notice", "insert_after": "custom_statutory_locked"},
			{"fieldname": "custom_malaysia_deduction_evidence", "label": "Deduction Approval Evidence", "fieldtype": "Attach", "insert_after": "custom_malaysia_final_pay_type"},
		],
		"Payroll Entry": [
			{"fieldname": "custom_malaysia_controls_section", "label": "Malaysia Controls", "fieldtype": "Section Break", "insert_after": "payroll_frequency", "collapsible": 1},
			{"fieldname": "custom_malaysia_enabled", "label": "Apply Malaysia Controls", "fieldtype": "Check", "default": "0", "insert_after": "custom_malaysia_controls_section"},
			{"fieldname": "custom_malaysia_final_run", "label": "Final Payroll for Contribution Month", "fieldtype": "Check", "default": "0", "insert_after": "custom_malaysia_enabled"},
			{"fieldname": "custom_malaysia_final_period_key", "label": "Final Period Key", "fieldtype": "Data", "insert_after": "custom_malaysia_final_run", "read_only": 1, "unique": 1, "no_copy": 1},
			{"fieldname": "custom_malaysia_control_state", "label": "Malaysia Control State", "fieldtype": "Select", "options": "Not Started\nValidation Failed\nValidated\nPayroll Generated\nAwaiting Human Release\nReleased\nCancelled", "default": "Not Started", "insert_after": "custom_malaysia_final_period_key", "read_only": 1},
			{"fieldname": "custom_malaysia_source_snapshot_hash", "label": "Malaysia Source Snapshot SHA-256", "fieldtype": "Data", "insert_after": "custom_malaysia_control_state", "read_only": 1, "no_copy": 1},
			{"fieldname": "custom_malaysia_work_record_reservation_status", "label": "Work Record Reservation Status", "fieldtype": "Select", "options": "Not Reserved\nReserved\nReleased", "default": "Not Reserved", "insert_after": "custom_malaysia_source_snapshot_hash", "read_only": 1},
			{"fieldname": "custom_malaysia_validation_errors", "label": "Malaysia Validation Errors", "fieldtype": "Code", "options": "JSON", "insert_after": "custom_malaysia_work_record_reservation_status", "read_only": 1},
			{"fieldname": "custom_malaysia_processed_by", "label": "Payroll Processed By", "fieldtype": "Link", "options": "User", "insert_after": "custom_malaysia_validation_errors", "read_only": 1, "no_copy": 1},
			{"fieldname": "custom_malaysia_released_by", "label": "Released By", "fieldtype": "Link", "options": "User", "insert_after": "custom_malaysia_processed_by", "read_only": 1},
			{"fieldname": "custom_malaysia_released_on", "label": "Released On", "fieldtype": "Datetime", "insert_after": "custom_malaysia_released_by", "read_only": 1},
			{"fieldname": "custom_malaysia_employer_contribution_journal", "label": "Malaysia Employer Contribution Journal", "fieldtype": "Link", "options": "Journal Entry", "insert_after": "custom_malaysia_released_on", "read_only": 1},
			{"fieldname": "custom_malaysia_employer_contribution_total", "label": "Malaysia Employer Contribution Total", "fieldtype": "Currency", "insert_after": "custom_malaysia_employer_contribution_journal", "read_only": 1},
			{"fieldname": "custom_malaysia_bank_file", "label": "Bank Payroll File", "fieldtype": "Attach", "insert_after": "custom_malaysia_employer_contribution_total", "read_only": 1},
			{"fieldname": "custom_malaysia_bank_file_hash", "label": "Bank File SHA-256", "fieldtype": "Data", "insert_after": "custom_malaysia_bank_file", "read_only": 1},
			{"fieldname": "custom_malaysia_bank_reconciliation_state", "label": "Bank Reconciliation State", "fieldtype": "Select", "options": "Not Generated\nPrepared\nAuthorised\nReconciled\nFailed", "default": "Not Generated", "insert_after": "custom_malaysia_bank_file_hash", "read_only": 1},
			{"fieldname": "custom_malaysia_bank_reference", "label": "Bank Batch Reference", "fieldtype": "Data", "insert_after": "custom_malaysia_bank_reconciliation_state", "read_only": 1},
			{"fieldname": "custom_malaysia_bank_paid_count", "label": "Bank Paid Employee Count", "fieldtype": "Int", "insert_after": "custom_malaysia_bank_reference", "read_only": 1},
			{"fieldname": "custom_malaysia_bank_paid_total", "label": "Bank Paid Total", "fieldtype": "Currency", "insert_after": "custom_malaysia_bank_paid_count", "read_only": 1},
			{"fieldname": "custom_malaysia_bank_difference", "label": "Bank Reconciliation Difference", "fieldtype": "Currency", "insert_after": "custom_malaysia_bank_paid_total", "read_only": 1},
			{"fieldname": "custom_malaysia_bank_evidence", "label": "Bank Reconciliation Evidence", "fieldtype": "Attach", "insert_after": "custom_malaysia_bank_difference", "read_only": 1},
			{"fieldname": "custom_malaysia_statutory_preparation_status", "label": "Statutory Preparation Status", "fieldtype": "Select", "options": "Not Started\nGenerated\nValidation Failed\nSubmitted\nReconciled", "default": "Not Started", "insert_after": "custom_malaysia_bank_evidence", "read_only": 1},
		],
		"Journal Entry": [
			{"fieldname": "custom_malaysia_payroll_entry", "label": "Malaysia Payroll Entry", "fieldtype": "Link", "options": "Payroll Entry", "insert_after": "user_remark", "read_only": 1, "search_index": 1},
			{"fieldname": "custom_malaysia_journal_key", "label": "Malaysia Journal Key", "fieldtype": "Data", "insert_after": "custom_malaysia_payroll_entry", "read_only": 1, "unique": 1, "no_copy": 1},
		],
		"ToDo": [
			{"fieldname": "custom_malaysia_exception_code", "label": "Malaysia Exception Code", "fieldtype": "Data", "insert_after": "priority", "read_only": 1},
			{"fieldname": "custom_malaysia_content_hash", "label": "Protected Content SHA-256", "fieldtype": "Data", "insert_after": "custom_malaysia_exception_code", "read_only": 1},
			{"fieldname": "custom_malaysia_resolution_evidence", "label": "Resolution Evidence", "fieldtype": "Attach", "insert_after": "custom_malaysia_content_hash"},
			{"fieldname": "custom_malaysia_resolved_by", "label": "Resolved By", "fieldtype": "Link", "options": "User", "insert_after": "custom_malaysia_resolution_evidence", "read_only": 1, "no_copy": 1},
			{"fieldname": "custom_malaysia_resolved_on", "label": "Resolved On", "fieldtype": "Datetime", "insert_after": "custom_malaysia_resolved_by", "read_only": 1, "no_copy": 1},
			{"fieldname": "custom_malaysia_resolution_hash", "label": "Resolution SHA-256", "fieldtype": "Data", "insert_after": "custom_malaysia_resolved_on", "read_only": 1, "no_copy": 1},
		],
		"Issue": [
			{"fieldname": "custom_malaysia_incident_section", "label": "Malaysia Workplace Incident", "fieldtype": "Section Break", "insert_after": "description", "collapsible": 1},
			{"fieldname": "custom_malaysia_workplace_incident", "label": "Workplace Incident", "fieldtype": "Check", "default": "0", "insert_after": "custom_malaysia_incident_section"},
			{"fieldname": "custom_incident_company", "label": "Company", "fieldtype": "Link", "options": "Company", "insert_after": "custom_malaysia_workplace_incident"},
			{"fieldname": "custom_incident_employee", "label": "Affected Employee", "fieldtype": "Link", "options": "Employee", "insert_after": "custom_incident_company"},
			{"fieldname": "custom_incident_occurred_on", "label": "Incident Occurred On", "fieldtype": "Datetime", "insert_after": "custom_incident_employee"},
			{"fieldname": "custom_perkeso_escalation_due", "label": "PERKESO Escalation Due", "fieldtype": "Datetime", "insert_after": "custom_incident_occurred_on", "read_only": 1},
			{"fieldname": "custom_dosh_reporting_required", "label": "DOSH Reporting Required", "fieldtype": "Check", "default": "0", "insert_after": "custom_perkeso_escalation_due"},
			{"fieldname": "custom_incident_report_evidence", "label": "Authority Report Evidence", "fieldtype": "Attach", "insert_after": "custom_dosh_reporting_required"},
		],
		"Training Event": [
			{"fieldname": "custom_hrd_corp_section", "label": "HRD Corp Evidence", "fieldtype": "Section Break", "insert_after": "description", "collapsible": 1},
			{"fieldname": "custom_hrd_corp_submission", "label": "HRD Corp Levy Submission", "fieldtype": "Link", "options": "Statutory Submission", "insert_after": "custom_hrd_corp_section"},
			{"fieldname": "custom_hrd_corp_grant_evidence", "label": "HRD Corp Grant / Claim Evidence", "fieldtype": "Attach", "insert_after": "custom_hrd_corp_submission"},
		],
	}
	if only_doctypes:
		custom_fields = {
			doctype: fields for doctype, fields in custom_fields.items() if doctype in only_doctypes
		}
	# SQLite is used only for the isolated developer test site. SQLite cannot add a
	# UNIQUE column to an existing table, so add the columns first and create the
	# equivalent unique indexes afterwards. MariaDB/Postgres keep Frappe's normal
	# Custom Field uniqueness path.
	unique_fields: list[tuple[str, str]] = []
	if frappe.db.db_type == "sqlite":
		for doctype, fields in custom_fields.items():
			for field in fields:
				if field.get("unique"):
					unique_fields.append((doctype, field["fieldname"]))
					field["unique"] = 0
	_create_custom_fields(custom_fields, update=True)
	for doctype, fieldname in unique_fields:
		frappe.db.add_unique(
			doctype,
			[fieldname],
			constraint_name=f"mw_unique_{doctype.lower().replace(' ', '_')}_{fieldname}",
		)
