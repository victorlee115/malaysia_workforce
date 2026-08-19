frappe.ui.form.on("Malaysia Statutory Filing", {
	refresh(frm) {
		if (frm.is_new() || !frm.perm?.[0]?.write) return;
		if (frm.doc.docstatus === 0) {
			const label = frm.doc.authority === "HRD Corp" ? __("Prepare Working Paper") : __("Prepare File");
			frm.add_custom_button(label, () => frm.call("prepare").then(() => frm.reload_doc()));
		}
		if (frm.doc.docstatus === 1 && frm.doc.reconciliation_status !== "Reconciled" && frm.doc.authority_status === "Accepted") {
			frm.add_custom_button(__("Reconcile"), () => frm.call("reconcile").then(() => frm.reload_doc()));
		}
	},
});
