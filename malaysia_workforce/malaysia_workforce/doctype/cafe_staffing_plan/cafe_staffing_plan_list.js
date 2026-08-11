frappe.listview_settings["Cafe Staffing Plan"] = {
	add_fields: ["workflow_state", "critical_uncovered_minutes", "unresolved_exception_count"],
	get_indicator(doc) {
		if (doc.unresolved_exception_count || doc.critical_uncovered_minutes) return [__("Needs Attention"), "orange", "unresolved_exception_count,>,0"];
		const colors = { Draft: "gray", "Collecting Availability": "blue", Proposed: "yellow", Approved: "green", Superseded: "gray" };
		return [__(doc.workflow_state || "Draft"), colors[doc.workflow_state] || "gray", `workflow_state,=,${doc.workflow_state || "Draft"}`];
	},
};
