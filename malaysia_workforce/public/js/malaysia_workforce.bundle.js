import "../css/malaysia_workforce.bundle.css";

const callDocMethod = (frm, method) =>
	frappe.call({
		doc: frm.doc,
		method,
		freeze: true,
		freeze_message: __("Working…"),
	}).then(() => frm.reload_doc());

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
				"HRD Corp": "hrd_corp_portal_url",
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
			__("Not Applicable treatment requires an HR Manager, a controlled reason, detailed notes and attached approval evidence. Changes are retained in immutable history."),
			"orange",
		);
	},
});
