frappe.ui.form.on("Malaysia Previous Employment TP3", {
	refresh(frm) {
		const privileged = frappe.user.has_role(["HR Manager", "System Manager"]);
		set_tp3_employee_defaults(frm, privileged);
		if (privileged && frm.doc.workflow_state === "Pending Review") {
			["employee", "company", "tax_year", "previous_employer_name", "previous_employer_number",
				"employment_start", "employment_end", "gross_normal_remuneration", "gross_additional_remuneration",
				"epf_contribution", "mtd_paid", "zakat_paid", "relief_claims", "evidence", "employee_declaration"]
				.forEach((fieldname) => frm.set_df_property(fieldname, "read_only", 1));
		}
	},
});

function set_tp3_employee_defaults(frm, privileged) {
	if (!frm.is_new() || privileged || frm.__employee_defaults_loaded) return;
	frm.__employee_defaults_loaded = true;
	["employee", "company"].forEach((fieldname) => frm.set_df_property(fieldname, "read_only", 1));
	frappe.call({
		method: "malaysia_workforce.permissions.employee_tax_defaults",
		callback: ({ message }) => message && frm.set_value(message),
	});
}
