from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields as _create_custom_fields


def create_custom_fields():
	custom_fields = {
		"Employee": [
			{"fieldname": "custom_malaysia_workforce_section", "label": "Malaysia Workforce", "fieldtype": "Section Break", "insert_after": "employment_type", "collapsible": 1},
			{"fieldname": "custom_work_arrangement", "label": "Work Arrangement", "fieldtype": "Select", "options": "Full Time\nPart Time\nCasual\nTemporary\nSeasonal\nContractor", "insert_after": "custom_malaysia_workforce_section"},
			{"fieldname": "custom_employee_work_agreement", "label": "Current Work Agreement", "fieldtype": "Link", "options": "Employee Work Agreement", "insert_after": "custom_work_arrangement", "read_only": 1},
			{"fieldname": "custom_malaysia_employee_profile", "label": "Malaysia Employee Profile", "fieldtype": "Link", "options": "Malaysia Employee Profile", "insert_after": "custom_employee_work_agreement", "read_only": 1},
			{"fieldname": "custom_statutory_coverage_profile", "label": "Statutory Coverage Profile", "fieldtype": "Link", "options": "Statutory Coverage Profile", "insert_after": "custom_malaysia_employee_profile", "read_only": 1},
			{"fieldname": "custom_roster_enabled", "label": "Available for Casual Rosters", "fieldtype": "Check", "default": "0", "insert_after": "custom_statutory_coverage_profile"},
			{"fieldname": "custom_malaysia_legal_jurisdiction", "label": "Malaysian Legal Jurisdiction", "fieldtype": "Select", "options": "Peninsular Malaysia\nSabah\nSarawak", "insert_after": "custom_roster_enabled"},
			{"fieldname": "custom_other_employment_declared", "label": "Other Employment Declared", "fieldtype": "Check", "default": "0", "insert_after": "custom_malaysia_legal_jurisdiction"},
		],
		"Company": [
			{"fieldname": "custom_malaysia_payroll_section", "label": "Malaysia Payroll", "fieldtype": "Section Break", "insert_after": "country", "collapsible": 1},
			{"fieldname": "custom_enable_malaysia_payroll", "label": "Enable Malaysia Payroll", "fieldtype": "Check", "default": "0", "insert_after": "custom_malaysia_payroll_section"},
			{"fieldname": "custom_lhdn_hq_number", "label": "LHDN HQ Number", "fieldtype": "Data", "insert_after": "custom_enable_malaysia_payroll"},
			{"fieldname": "custom_lhdn_employer_number", "label": "LHDN Employer Number", "fieldtype": "Data", "insert_after": "custom_lhdn_hq_number"},
			{"fieldname": "custom_epf_employer_number", "label": "EPF Employer Number", "fieldtype": "Data", "insert_after": "custom_lhdn_employer_number"},
			{"fieldname": "custom_socso_employer_code", "label": "SOCSO Employer Code", "fieldtype": "Data", "insert_after": "custom_epf_employer_number"},
			{"fieldname": "custom_company_registration_number", "label": "SSM / Company Registration Number", "fieldtype": "Data", "insert_after": "custom_socso_employer_code"},
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
		],
		"Shift Assignment": [
			{"fieldname": "custom_malaysia_roster_section", "label": "Malaysia Roster", "fieldtype": "Section Break", "insert_after": "shift_schedule_assignment", "collapsible": 1},
			{"fieldname": "custom_casual_roster", "label": "Casual Roster", "fieldtype": "Link", "options": "Casual Roster", "insert_after": "custom_malaysia_roster_section", "read_only": 1},
			{"fieldname": "custom_roster_selection", "label": "Roster Selection", "fieldtype": "Link", "options": "Roster Selection", "insert_after": "custom_casual_roster", "read_only": 1, "search_index": 1},
			{"fieldname": "custom_assigned_start_datetime", "label": "Assigned Start", "fieldtype": "Datetime", "insert_after": "custom_roster_selection", "read_only": 1},
			{"fieldname": "custom_assigned_end_datetime", "label": "Assigned End", "fieldtype": "Datetime", "insert_after": "custom_assigned_start_datetime", "read_only": 1},
			{"fieldname": "custom_assigned_hourly_rate", "label": "Assigned Hourly Rate", "fieldtype": "Currency", "insert_after": "custom_assigned_end_datetime", "read_only": 1},
			{"fieldname": "custom_assigned_role", "label": "Assigned Role", "fieldtype": "Data", "insert_after": "custom_assigned_hourly_rate", "read_only": 1},
			{"fieldname": "custom_shift_work_record", "label": "Shift Work Record", "fieldtype": "Link", "options": "Shift Work Record", "insert_after": "custom_assigned_role", "read_only": 1},
		],
		"Shift Type": [
			{"fieldname": "custom_dynamic_roster_shift", "label": "Dynamic Malaysia Roster Shift", "fieldtype": "Check", "default": "0", "insert_after": "color", "read_only": 1},
			{"fieldname": "custom_mw_configuration_fingerprint", "label": "Malaysia Shift Configuration Fingerprint", "fieldtype": "Data", "insert_after": "custom_dynamic_roster_shift", "read_only": 1, "search_index": 1},
		],
		"Employee Checkin": [
			{"fieldname": "custom_malaysia_checkin_section", "label": "Malaysia Workforce", "fieldtype": "Section Break", "insert_after": "device_id", "collapsible": 1},
			{"fieldname": "custom_roster_selection", "label": "Roster Selection", "fieldtype": "Link", "options": "Roster Selection", "insert_after": "custom_malaysia_checkin_section", "read_only": 1},
			{"fieldname": "custom_shift_work_record", "label": "Shift Work Record", "fieldtype": "Link", "options": "Shift Work Record", "insert_after": "custom_roster_selection", "read_only": 1},
			{"fieldname": "custom_checkin_method", "label": "Check-in Method", "fieldtype": "Select", "options": "\nMobile\nQR\nKiosk\nBiometric\nManual\nIntegration", "insert_after": "custom_shift_work_record"},
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
			{"fieldname": "custom_malaysia_payroll_run", "label": "Malaysia Payroll Run", "fieldtype": "Link", "options": "Malaysia Payroll Run", "insert_after": "custom_malaysia_statutory_snapshot", "read_only": 1},
			{"fieldname": "custom_statutory_recalculation_required", "label": "Statutory Recalculation Required", "fieldtype": "Check", "default": "0", "insert_after": "custom_malaysia_payroll_run", "read_only": 1},
			{"fieldname": "custom_statutory_locked", "label": "Statutory Snapshot Locked", "fieldtype": "Check", "default": "0", "insert_after": "custom_statutory_recalculation_required", "read_only": 1},
		],
		"Payroll Entry": [
			{"fieldname": "custom_malaysia_payroll_run", "label": "Malaysia Payroll Run", "fieldtype": "Link", "options": "Malaysia Payroll Run", "insert_after": "payroll_frequency", "read_only": 1},
		],
		"Journal Entry": [
			{"fieldname": "custom_malaysia_payroll_run", "label": "Malaysia Payroll Run", "fieldtype": "Link", "options": "Malaysia Payroll Run", "insert_after": "user_remark", "read_only": 1, "search_index": 1},
		],
	}
	_create_custom_fields(custom_fields, update=True)
