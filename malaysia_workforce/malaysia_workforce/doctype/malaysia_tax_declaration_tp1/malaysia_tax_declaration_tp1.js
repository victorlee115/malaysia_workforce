frappe.ui.form.on("Malaysia Tax Declaration TP1", {
	refresh(frm) {
		set_tp1_employee_defaults(frm);
		apply_tax_permissions(frm);
		load_relief_catalog(frm);
	},
	tax_year(frm) {
		load_relief_catalog(frm);
	},
});

function apply_tax_permissions(frm) {
	const privileged = frappe.user.has_role(["HR Manager", "System Manager"]);
	frm.set_df_property("review_section", "hidden", !privileged);
	if (privileged && frm.doc.workflow_state === "Pending Review") {
		frm.set_df_property("review_section", "collapsed", 0);
		["employee", "company", "tax_year", "declaration_date", "relief_claims", "employee_declaration"]
			.forEach((fieldname) => frm.set_df_property(fieldname, "read_only", 1));
	}
}

function set_tp1_employee_defaults(frm) {
	const privileged = frappe.user.has_role(["HR Manager", "System Manager"]);
	if (!frm.is_new() || privileged || frm.__employee_defaults_loaded) return;
	frm.__employee_defaults_loaded = true;
	["employee", "company"].forEach((fieldname) => frm.set_df_property(fieldname, "read_only", 1));
	frappe.call({
		method: "malaysia_workforce.permissions.employee_tax_defaults",
		callback: ({ message }) => {
			if (!message) return;
			frm.set_value(message).then(() => load_relief_catalog(frm));
		},
	});
}

frappe.ui.form.on("Malaysia Tax Relief Claim", {
	relief_code(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		const code = String(row.relief_code || "").trim().split(/\s+/)[0];
		row.description = frm._tp1_catalog?.[code] || "";
		frm.refresh_field("relief_claims");
	},
});

function load_relief_catalog(frm) {
	if (!frm.doc.tax_year) return;
	frappe.call({
		method: "malaysia_workforce.malaysia_workforce.doctype.malaysia_tax_declaration_tp1.malaysia_tax_declaration_tp1.relief_catalog",
		args: { tax_year: frm.doc.tax_year },
		callback: ({ message }) => {
			frm._tp1_catalog = message || {};
			(frm.doc.relief_claims || []).forEach((row) => {
				const code = String(row.relief_code || "").trim().split(/\s+/)[0];
				row.description = frm._tp1_catalog[code] || row.description;
			});
			frm.refresh_field("relief_claims");
		},
	});
}
