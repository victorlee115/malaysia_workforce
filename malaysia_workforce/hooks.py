app_name = "malaysia_workforce"
app_title = "Malaysia Payroll"
app_publisher = "Malaysia Workforce contributors"
app_description = "Malaysian payroll and statutory localisation for Frappe HR"
app_license = "GNU General Public License (v3)"
required_apps = ["erpnext", "hrms"]

before_install = "malaysia_workforce.install.before_install"
after_install = "malaysia_workforce.install.after_install"
before_migrate = "malaysia_workforce.install.before_migrate"
after_migrate = "malaysia_workforce.install.after_migrate"

doc_events = {
	"Company": {
		"validate": "malaysia_workforce.payroll.validation.validate_company",
	},
	"Employee": {
		"validate": "malaysia_workforce.payroll.validation.validate_employee",
	},
	"Contract": {
		"validate": "malaysia_workforce.payroll.validation.validate_contract",
	},
	"Salary Component": {
		"validate": "malaysia_workforce.payroll.validation.validate_salary_component",
	},
	"Salary Slip": {
		"validate": "malaysia_workforce.payroll.salary_slip.apply_malaysia_statutory_calculations",
		"before_cancel": "malaysia_workforce.payroll.salary_slip.protect_filed_salary_slip",
	},
	"Payroll Entry": {
		"before_submit": "malaysia_workforce.payroll.events.validate_payroll_release",
	},
}

extend_doctype_class = {
	"Overtime Slip": ["malaysia_workforce.payroll.overtime.MalaysiaOvertimeMixin"],
}

doctype_js = {
	"Payroll Entry": "public/js/payroll_entry.js",
}

permission_query_conditions = {
	"Malaysia Tax Declaration TP1": "malaysia_workforce.permissions.tp1_query",
	"Malaysia Previous Employment TP3": "malaysia_workforce.permissions.tp3_query",
	"Malaysia CP38 Directive": "malaysia_workforce.permissions.cp38_query",
	"Malaysia Statutory Filing": "malaysia_workforce.permissions.filing_query",
}

has_permission = {
	"Malaysia Tax Declaration TP1": "malaysia_workforce.permissions.employee_tax_permission",
	"Malaysia Previous Employment TP3": "malaysia_workforce.permissions.employee_tax_permission",
	"Malaysia CP38 Directive": "malaysia_workforce.permissions.company_permission",
	"Malaysia Statutory Filing": "malaysia_workforce.permissions.company_permission",
}
