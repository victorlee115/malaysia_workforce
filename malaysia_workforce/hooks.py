app_name = "malaysia_workforce"
app_title = "Malaysia Workforce"
app_publisher = "Malaysia Workforce contributors"
app_description = "Frappe HR staffing and Malaysian payroll/statutory localisation"
app_license = "GNU General Public License (v3)"
required_apps = ["erpnext", "hrms"]

app_include_css = ["malaysia_workforce.bundle.css"]
app_include_js = ["malaysia_workforce.bundle.js"]

standard_portal_menu_items = [
	{"title": "My Availability", "route": "/casual-availability", "reference_doctype": "Casual Availability"},
]

before_install = "malaysia_workforce.install.before_install"
after_install = "malaysia_workforce.install.after_install"
before_migrate = "malaysia_workforce.install.before_migrate"
after_migrate = "malaysia_workforce.install.after_migrate"
before_uninstall = "malaysia_workforce.install.before_uninstall"

fixtures = [
	{"dt": "Role", "filters": [["name", "in", ["Casual Employee", "Outlet Manager", "Malaysia Payroll User", "Malaysia HR Manager", "Malaysia Kiosk", "Statutory Administrator", "Malaysia Workforce Auditor"]]]},
]

doc_events = {
	"Employee": {
		"validate": [
			"malaysia_workforce.staffing.validation.validate_staffing_priority",
			"malaysia_workforce.compliance.privacy.validate_privacy_acknowledgement",
			"malaysia_workforce.compliance.scope.validate_employee_scope",
		],
	},
	"Employee Checkin": {
		"validate": "malaysia_workforce.attendance.events.protect_employee_checkin_evidence",
		"after_insert": "malaysia_workforce.attendance.events.on_employee_checkin",
		"on_trash": "malaysia_workforce.attendance.events.prevent_employee_checkin_evidence_deletion",
	},
	"Shift Assignment": {
		"on_submit": "malaysia_workforce.attendance.events.on_shift_assignment_submit",
		"on_cancel": "malaysia_workforce.attendance.events.on_shift_assignment_cancel",
	},
	"Shift Type": {
		"on_trash": "malaysia_workforce.staffing.shift_types.prevent_managed_shift_deletion",
	},
	"Salary Slip": {
		"validate": "malaysia_workforce.payroll.salary_slip.apply_malaysia_statutory_calculations",
		"on_submit": "malaysia_workforce.payroll.salary_slip.freeze_statutory_snapshot",
		"before_cancel": "malaysia_workforce.payroll.salary_slip.before_salary_slip_cancel",
		"on_cancel": "malaysia_workforce.payroll.salary_slip.reopen_accumulator",
	},
	"Payroll Entry": {
		"validate": [
			"malaysia_workforce.compliance.scope.validate_payroll_entry_scope",
			"malaysia_workforce.payroll.events.validate_payroll_readiness",
		],
		"on_submit": "malaysia_workforce.payroll.events.on_payroll_entry_submit",
		"before_cancel": "malaysia_workforce.payroll.events.before_payroll_entry_cancel",
		"on_cancel": "malaysia_workforce.payroll.events.on_payroll_entry_cancel",
	},
	"Additional Salary": {
		"on_cancel": "malaysia_workforce.payroll.events.on_additional_salary_cancel",
	},
	"Expense Claim": {
		"validate": "malaysia_workforce.compliance.approvals.prevent_self_approval",
	},
	"Attendance Request": {
		"validate": "malaysia_workforce.compliance.approvals.prevent_self_approval",
	},
	"ToDo": {
		"validate": "malaysia_workforce.compliance.exceptions.validate_exception_todo",
	},
}

doctype_js = {
	"Payroll Entry": "public/js/payroll_entry.js",
}

scheduler_events = {
	"hourly": [
		"malaysia_workforce.attendance.jobs.reconcile_recent_work_records",
		"malaysia_workforce.staffing.jobs.close_availability_windows",
	],
	"daily": [
		"malaysia_workforce.staffing.jobs.send_availability_reminders",
		"malaysia_workforce.staffing.jobs.flag_staffing_deadlines",
		"malaysia_workforce.staffing.jobs.flag_stale_staffing_proposals",
		"malaysia_workforce.staffing.jobs.expire_staffing_priorities",
		"malaysia_workforce.compliance.jobs.refresh_obligations",
		"malaysia_workforce.compliance.jobs.flag_expired_overrides",
		"malaysia_workforce.compliance.jobs.refresh_control_deadlines",
	],
	"daily_long": [
		"malaysia_workforce.payroll.jobs.rebuild_open_accumulators",
	],
}

permission_query_conditions = {
	"Casual Availability": "malaysia_workforce.permissions.casual_availability_query_condition",
	"Cafe Coverage Template": "malaysia_workforce.permissions.coverage_template_query_condition",
	"Cafe Staffing Plan": "malaysia_workforce.permissions.staffing_plan_query_condition",
	"Shift Work Record": "malaysia_workforce.permissions.shift_work_record_query_condition",
	"Malaysia Tax Declaration TP1": "malaysia_workforce.permissions.tp1_query_condition",
	"Malaysia Previous Employment TP3": "malaysia_workforce.permissions.tp3_query_condition",
	"Malaysia Annual Remuneration Statement": "malaysia_workforce.permissions.annual_statement_query_condition",
	"Malaysia Employee Profile": "malaysia_workforce.permissions.employee_profile_query_condition",
	"Employee Work Agreement": "malaysia_workforce.permissions.work_agreement_query_condition",
	"Statutory Coverage Profile": "malaysia_workforce.permissions.coverage_profile_query_condition",
	"Monthly Statutory Accumulator": "malaysia_workforce.permissions.accumulator_query_condition",
	"Statutory Submission": "malaysia_workforce.permissions.submission_query_condition",
	"Malaysia Employee Notification": "malaysia_workforce.permissions.employee_notification_query_condition",
	"Statutory Treatment History": "malaysia_workforce.permissions.treatment_history_query_condition",
}

has_permission = {
	"Casual Availability": "malaysia_workforce.permissions.casual_availability_has_permission",
	"Cafe Coverage Template": "malaysia_workforce.permissions.staffing_has_permission",
	"Cafe Staffing Plan": "malaysia_workforce.permissions.staffing_has_permission",
	"Shift Work Record": "malaysia_workforce.permissions.shift_work_record_has_permission",
	"Malaysia Tax Declaration TP1": "malaysia_workforce.permissions.employee_owned_tax_has_permission",
	"Malaysia Previous Employment TP3": "malaysia_workforce.permissions.employee_owned_tax_has_permission",
	"Malaysia Annual Remuneration Statement": "malaysia_workforce.permissions.employee_owned_tax_has_permission",
	"Malaysia Employee Profile": "malaysia_workforce.permissions.company_scoped_has_permission",
	"Employee Work Agreement": "malaysia_workforce.permissions.company_scoped_has_permission",
	"Statutory Coverage Profile": "malaysia_workforce.permissions.company_scoped_has_permission",
	"Monthly Statutory Accumulator": "malaysia_workforce.permissions.company_scoped_has_permission",
	"Statutory Submission": "malaysia_workforce.permissions.company_scoped_has_permission",
	"Malaysia Employee Notification": "malaysia_workforce.permissions.company_scoped_has_permission",
	"Statutory Treatment History": "malaysia_workforce.permissions.employee_company_scoped_has_permission",
}
