frappe.query_reports["Cafe Coverage Gaps"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", reqd: 1, default: frappe.defaults.get_user_default("Company") },
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", default: frappe.datetime.get_today() },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", default: frappe.datetime.add_days(frappe.datetime.get_today(), 28) },
		{ fieldname: "critical_only", label: __("Critical Only"), fieldtype: "Check", default: 0 },
	],
};
