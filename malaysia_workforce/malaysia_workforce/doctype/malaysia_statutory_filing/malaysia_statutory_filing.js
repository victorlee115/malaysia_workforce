frappe.ui.form.on("Malaysia Statutory Filing", {
	refresh(frm) {
		if (frm.is_new() || !frm.perm?.[0]?.write) return;
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Prepare File"), () => frm.call("prepare").then(() => frm.reload_doc()));
		}
		if (frm.doc.docstatus === 1 && frm.doc.reconciliation_status !== "Reconciled") {
			frm.add_custom_button(__("Reconcile"), () => frm.call("reconcile").then(() => frm.reload_doc()));
		}
	},
});
