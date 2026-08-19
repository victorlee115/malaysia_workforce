frappe.ui.form.on("Malaysia Previous Employment TP3", {
	refresh(frm) {
		const privileged = frappe.user.has_role(["HR Manager", "System Manager"]);
		set_tp3_employee_defaults(frm, privileged);
		if (privileged && frm.doc.workflow_state === "Pending Review") {
			frm.set_df_property("review_section", "collapsed", 0);
			["employee", "company", "tax_year", "previous_employer_name", "previous_employer_number",
				"employment_start", "employment_end", "gross_normal_remuneration", "gross_additional_remuneration",
				"epf_contribution", "mtd_paid", "zakat_paid", "relief_claims", "evidence", "employee_declaration"]
				.forEach((fieldname) => frm.set_df_property(fieldname, "read_only", 1));
		}
		load_relief_catalog(frm);
	},
	tax_year(frm) {
		load_relief_catalog(frm);
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

frappe.ui.form.on("Malaysia Tax Relief Claim", {
	relief_code(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		const code = String(row.relief_code || "").trim().split(/\s+/)[0];
		row.description = frm._tp3_catalog?.[code] || "";
		frm.refresh_field("relief_claims");
	},
});

function load_relief_catalog(frm) {
	if (!frm.doc.tax_year) return;
	frappe.call({
		method: "malaysia_workforce.malaysia_workforce.doctype.malaysia_tax_declaration_tp1.malaysia_tax_declaration_tp1.relief_catalog",
		args: { tax_year: frm.doc.tax_year },
		callback: ({ message }) => {
			frm._tp3_catalog = message || {};
			(frm.doc.relief_claims || []).forEach((row) => {
				const code = String(row.relief_code || "").trim().split(/\s+/)[0];
				row.description = frm._tp3_catalog[code] || row.description;
			});
			frm.refresh_field("relief_claims");
		},
	});
}
