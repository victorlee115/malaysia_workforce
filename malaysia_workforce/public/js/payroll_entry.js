frappe.ui.form.on("Payroll Entry", {
	// HRMS calls has_bank_entries with frm.call() while rendering every submitted
	// Payroll Entry. Frappe consequently re-checks "submit" permission on the
	// serialized document, which raises a permission dialog for legitimate
	// read-only releasers and auditors. Keep the native button for processors,
	// but do not make the mutating document-method call for read-only viewers.
	add_bank_entry_button(frm) {
		if (!frappe.perm.has_perm("Payroll Entry", 0, "submit", frm.doc)) {
			return;
		}
		frm.call("has_bank_entries").then((r) => {
			if (!r.message.has_bank_entries) {
				frm.add_custom_button(__("Make Bank Entry"), () => make_bank_entry(frm)).addClass("btn-primary");
			} else if (!r.message.has_bank_entries_for_withheld_salaries) {
				frm.add_custom_button(__("Release Withheld Salaries"), () => make_bank_entry(frm, 1)).addClass("btn-primary");
			}
		});
	},
	refresh(frm) {
		if (!frm.doc.custom_malaysia_enabled) {
			return;
		}
		const roles = new Set(frappe.user_roles || []);
		const can_process = ["Malaysia Payroll User", "System Manager"].some((role) => roles.has(role));
		const can_release = ["HR Manager", "Malaysia HR Manager", "System Manager"].some((role) => roles.has(role));
		if (frm.doc.docstatus === 0 && !frm.is_new()) {
			if (!can_process) return;
			frm.add_custom_button(__("Prepare Malaysia Inputs"), () => {
				frappe.call({
					method: "malaysia_workforce.payroll.services.prepare_payroll_entry",
					type: "POST",
					args: { payroll_entry: frm.doc.name },
					freeze: true,
					freeze_message: __("Validating work records and creating Additional Salary records…"),
					callback: () => frm.reload_doc(),
				});
			}, __("Malaysia Controls"));
			return;
		}
		if (frm.doc.docstatus !== 1) return;
		if (can_process) {
			frm.add_custom_button(__("Prepare Bank File"), () => {
				frappe.call({
					method: "malaysia_workforce.banking.service.prepare_bank_file",
					type: "POST",
					args: { payroll_entry: frm.doc.name },
					freeze: true,
					callback: () => frm.reload_doc(),
				});
			}, __("Malaysia Controls"));
		}
		if (can_release && frm.doc.custom_malaysia_control_state === "Awaiting Human Release") {
			frm.add_custom_button(__("Release Payroll"), () => {
				frappe.confirm(__("Confirm the bank file totals and authorise this payroll for upload?"), () => {
					frappe.call({
						method: "malaysia_workforce.banking.service.release_payroll",
						type: "POST",
						args: { payroll_entry: frm.doc.name },
						freeze: true,
						callback: () => frm.reload_doc(),
					});
				});
			}, __("Malaysia Controls"));
		}
		if (can_release && frm.doc.custom_malaysia_control_state === "Released" && frm.doc.custom_malaysia_bank_reconciliation_state !== "Reconciled") {
			frm.add_custom_button(__("Record Bank Reconciliation"), () => {
				const dialog = new frappe.ui.Dialog({
					title: __("Bank Reconciliation"),
					fields: [
						{ fieldname: "bank_reference", fieldtype: "Data", label: __("Bank Batch Reference"), reqd: 1 },
						{ fieldname: "paid_employee_count", fieldtype: "Int", label: __("Paid Employee Count"), reqd: 1 },
						{ fieldname: "paid_total", fieldtype: "Currency", label: __("Paid Total"), reqd: 1 },
						{ fieldname: "evidence", fieldtype: "Attach", label: __("Bank Evidence"), reqd: 1 },
					],
					primary_action_label: __("Reconcile"),
					primary_action(values) {
						frappe.call({
							method: "malaysia_workforce.banking.service.reconcile_bank_file",
							type: "POST",
							args: { payroll_entry: frm.doc.name, ...values },
							freeze: true,
							callback: () => { dialog.hide(); frm.reload_doc(); },
						});
					},
				});
				dialog.show();
			}, __("Malaysia Controls"));
		}
	},
});
