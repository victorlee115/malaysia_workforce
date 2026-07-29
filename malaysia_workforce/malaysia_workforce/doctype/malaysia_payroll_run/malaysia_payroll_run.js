frappe.ui.form.on("Malaysia Payroll Run", {
	refresh(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button(__("Collect & Validate"), () => runAction(frm, "collect_and_validate"), __("Payroll"));
		frm.add_custom_button(
			__("Create Missing Casual Assignments"),
			() =>
				frappe.confirm(
					__("Create the standard casual salary structure and assignments only for eligible workers without an assignment?"),
					() => runAction(frm, "create_missing_casual_assignments"),
				),
			__("Payroll"),
		);
		frm.add_custom_button(
			__("Generate Additional Salaries"),
			() =>
				frappe.confirm(
					__("Freeze the current approved work-record set and generate Additional Salary records? Later work must use an adjustment run."),
					() => runAction(frm, "generate_additional_salaries"),
				),
			__("Payroll"),
		);
		frm.add_custom_button(__("Create Payroll Entry"), () => runAction(frm, "create_payroll_entry", true), __("Payroll"));

		if (frm.doc.payroll_entry) {
			frm.add_custom_button(__("Open Payroll Entry"), () => frappe.set_route("Form", "Payroll Entry", frm.doc.payroll_entry));
		}
	},
});

async function runAction(frm, method, routeToPayroll = false) {
	const response = await frm.call({ method, freeze: true, freeze_message: __("Processing payroll…") });
	await frm.reload_doc();
	if (routeToPayroll && response.message) {
		frappe.set_route("Form", "Payroll Entry", response.message);
	} else if (response.message?.errors?.length) {
		frappe.msgprint({
			title: __("Payroll readiness issues"),
			message: response.message.errors.map((item) => frappe.utils.escape_html(item)).join("<br>"),
			indicator: "red",
		});
	} else {
		frappe.show_alert({ message: __("Completed"), indicator: "green" });
	}
}
