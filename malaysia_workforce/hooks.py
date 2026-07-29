app_name = "malaysia_workforce"
app_title = "Malaysia Workforce"
app_publisher = "Malaysia Workforce contributors"
app_description = "Malaysian workforce, casual roster, payroll and statutory localisation"
app_license = "GNU General Public License (v3)"
required_apps = ["erpnext", "hrms"]

add_to_apps_screen = [
	{
		"name": "malaysia_workforce",
		"logo": "/assets/malaysia_workforce/images/logo.svg",
		"title": "Malaysia Workforce",
		"route": "/desk/malaysia-workforce",
		"has_permission": "malaysia_workforce.permissions.can_access_app",
	}
]

app_include_css = ["malaysia_workforce.bundle.css"]
app_include_js = ["malaysia_workforce.bundle.js"]
web_include_css = ["/assets/malaysia_workforce/css/workforce_portal.css"]
web_include_js = ["/assets/malaysia_workforce/js/workforce_portal.js"]

website_route_rules = [
	{"from_route": "/workforce/<path:app_path>", "to_route": "workforce"},
]

before_install = "malaysia_workforce.install.before_install"
after_install = "malaysia_workforce.install.after_install"
after_migrate = "malaysia_workforce.install.after_migrate"
before_uninstall = "malaysia_workforce.install.before_uninstall"

fixtures = [
	{"dt": "Role", "filters": [["name", "in", ["Casual Employee", "Roster Manager", "Malaysia Payroll User", "Malaysia HR Manager", "Statutory Administrator"]]]},
]

doc_events = {
	"Employee Checkin": {
		"after_insert": "malaysia_workforce.attendance.events.on_employee_checkin",
	},
	"Shift Assignment": {
		"on_submit": "malaysia_workforce.attendance.events.on_shift_assignment_submit",
		"on_cancel": "malaysia_workforce.attendance.events.on_shift_assignment_cancel",
	},
	"Salary Slip": {
		"validate": "malaysia_workforce.payroll.salary_slip.apply_malaysia_statutory_calculations",
		"on_submit": "malaysia_workforce.payroll.salary_slip.freeze_statutory_snapshot",
		"on_cancel": "malaysia_workforce.payroll.salary_slip.reopen_accumulator",
	},
	"Payroll Entry": {
		"validate": "malaysia_workforce.payroll.events.validate_payroll_readiness",
		"on_submit": "malaysia_workforce.payroll.events.on_payroll_entry_submit",
		"before_cancel": "malaysia_workforce.payroll.events.before_payroll_entry_cancel",
		"on_cancel": "malaysia_workforce.payroll.events.on_payroll_entry_cancel",
	},
	"Additional Salary": {
		"on_cancel": "malaysia_workforce.payroll.events.on_additional_salary_cancel",
	},
}

scheduler_events = {
	"hourly": [
		"malaysia_workforce.roster.jobs.close_expired_rosters",
		"malaysia_workforce.roster.jobs.process_expired_standby_offers",
		"malaysia_workforce.attendance.jobs.reconcile_recent_work_records",
	],
	"daily": [
		"malaysia_workforce.roster.jobs.send_application_reminders",
		"malaysia_workforce.compliance.jobs.refresh_obligations",
		"malaysia_workforce.compliance.jobs.flag_expired_overrides",
	],
	"daily_long": [
		"malaysia_workforce.payroll.jobs.rebuild_open_accumulators",
	],
}

permission_query_conditions = {
	"Casual Roster": "malaysia_workforce.permissions.roster_query_condition",
	"Roster Application": "malaysia_workforce.permissions.roster_application_query_condition",
	"Roster Selection": "malaysia_workforce.permissions.roster_selection_query_condition",
	"Shift Work Record": "malaysia_workforce.permissions.shift_work_record_query_condition",
	"Roster Standby": "malaysia_workforce.permissions.roster_standby_query_condition",
	"Malaysia Tax Declaration TP1": "malaysia_workforce.permissions.tp1_query_condition",
	"Malaysia Previous Employment TP3": "malaysia_workforce.permissions.tp3_query_condition",
	"Malaysia Annual Remuneration Statement": "malaysia_workforce.permissions.annual_statement_query_condition",
}

has_permission = {
	"Casual Roster": "malaysia_workforce.permissions.roster_has_permission",
	"Roster Application": "malaysia_workforce.permissions.roster_application_has_permission",
	"Roster Selection": "malaysia_workforce.permissions.roster_selection_has_permission",
	"Shift Work Record": "malaysia_workforce.permissions.shift_work_record_has_permission",
	"Roster Standby": "malaysia_workforce.permissions.roster_standby_has_permission",
	"Malaysia Tax Declaration TP1": "malaysia_workforce.permissions.employee_owned_tax_has_permission",
	"Malaysia Previous Employment TP3": "malaysia_workforce.permissions.employee_owned_tax_has_permission",
	"Malaysia Annual Remuneration Statement": "malaysia_workforce.permissions.employee_owned_tax_has_permission",
}
