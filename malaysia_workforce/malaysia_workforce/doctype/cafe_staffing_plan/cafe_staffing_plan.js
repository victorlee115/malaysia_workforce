frappe.ui.form.on("Cafe Staffing Plan", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.dashboard.add_indicator(__("Coverage: {0}%", [flt(frm.doc.coverage_percent, 2)]), frm.doc.critical_uncovered_minutes ? "orange" : "green");
			if (frm.doc.unresolved_exception_count) {
				frm.dashboard.add_indicator(__("{0} need attention", [frm.doc.unresolved_exception_count]), "orange");
			}
		}
		if (frm.doc.docstatus === 1 && frm.doc.workflow_state === "Approved") {
			frm.add_custom_button(__("View Published Roster"), () => frappe.set_route("hr", "roster"));
		}
	},
});
