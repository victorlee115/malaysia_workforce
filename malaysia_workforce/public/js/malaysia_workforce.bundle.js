import "../css/malaysia_workforce.bundle.css";

const callDocMethod = (frm, method) =>
	frappe.call({
		doc: frm.doc,
		method,
		freeze: true,
		freeze_message: __("Working…"),
	}).then(() => frm.reload_doc());

frappe.ui.form.on("Casual Roster", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Open Planner"), () => {
				frappe.set_route("casual-roster-planner", frm.doc.name);
			});
		}
		if (frm.doc.status === "Draft" || frm.doc.status === "Applications Closed") {
			frm.add_custom_button(__("Open Applications"), () => callDocMethod(frm, "open_for_applications"), __("Actions"));
		}
		if (frm.doc.status === "Open for Applications") {
			frm.add_custom_button(__("Close Applications"), () => callDocMethod(frm, "close_applications"), __("Actions"));
		}
	},
});

frappe.ui.form.on("Malaysia Payroll Run", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("1. Validate"), () => callDocMethod(frm, "collect_and_validate"), __("Payroll"));
		frm.add_custom_button(__("2. Create Missing Casual Assignments"), () => callDocMethod(frm, "create_missing_casual_assignments"), __("Payroll"));
		frm.add_custom_button(__("3. Generate Additional Salary"), () => callDocMethod(frm, "generate_additional_salaries"), __("Payroll"));
		frm.add_custom_button(__("4. Create Payroll Entry"), async () => {
			const result = await frappe.call({doc: frm.doc, method: "create_payroll_entry", freeze: true});
			if (result.message) frappe.set_route("Form", "Payroll Entry", result.message);
		}, __("Payroll"));
	},
});

frappe.ui.form.on("Statutory Submission", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Load Payroll Data"), () => callDocMethod(frm, "load_from_payroll"), __("Submission"));
		frm.add_custom_button(__("Generate File"), async () => {
			const result = await frappe.call({doc: frm.doc, method: "generate_file", freeze: true});
			await frm.reload_doc();
			if (result.message?.file_url) window.open(result.message.file_url, "_blank", "noopener");
		}, __("Submission"));
		if (frm.doc.status === "Ready for Portal") {
			const portals = {
				LHDN: "lhdn_portal_url",
				EPF: "epf_portal_url",
				PERKESO: "perkeso_portal_url",
			};
			frm.add_custom_button(__("Open Official Portal"), async () => {
				const settings = await frappe.db.get_single_value("Malaysia Workforce Settings", portals[frm.doc.authority]);
				if (settings) window.open(settings, "_blank", "noopener,noreferrer");
			}, __("Submission"));
		}
	},
});

frappe.ui.form.on("Shift Work Record", {
	refresh(frm) {
		if (frm.doc.docstatus === 0 && ["Manager Review", "Automatically Verified"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Approve and Submit"), async () => {
				frm.set_value("status", "Approved");
				await frm.save();
				await frm.savesubmit();
			});
		}
	},
});

frappe.ui.form.on("Statutory Coverage Profile", {
	refresh(frm) {
		frm.set_intro(
			__("Authorised users can save Not Applicable immediately. The system records an immutable audit history but does not require approval."),
			"orange",
		);
	},
});
