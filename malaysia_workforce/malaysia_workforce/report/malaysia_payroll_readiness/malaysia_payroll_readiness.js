frappe.query_reports["Malaysia Payroll Readiness"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", reqd: 1, default: frappe.defaults.get_user_default("Company") },
		{ fieldname: "payroll_date", label: __("Payroll Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.month_end() },
		{ fieldname: "show_ready", label: __("Show Ready Employees"), fieldtype: "Check", default: 0 }
	]
};
