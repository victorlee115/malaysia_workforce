frappe.query_reports["Malaysia Annual Remuneration"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", reqd: 1, default: frappe.defaults.get_user_default("Company") },
		{ fieldname: "year", label: __("Year"), fieldtype: "Int", reqd: 1, default: new Date().getFullYear() }
	]
};
