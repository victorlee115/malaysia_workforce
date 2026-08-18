frappe.query_reports["Malaysia Payroll Readiness"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", reqd: 1, default: frappe.defaults.get_user_default("Company") },
		{ fieldname: "payroll_date", label: __("Payroll Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.month_end() },
		{ fieldname: "show_ready", label: __("Show Ready Employees"), fieldtype: "Check", default: 0 }
	],
	onload(report) {
		if (report.get_filter_value("company")) return;
		const company = malaysia_workforce_sole_permitted_company();
		if (company) report.set_filter_value("company", company);
	}
};

function malaysia_workforce_sole_permitted_company() {
	const rows = (frappe.defaults.get_user_permissions() || {}).Company || [];
	if (rows.length !== 1) return "";
	return rows[0].doc || rows[0].name || rows[0];
}
