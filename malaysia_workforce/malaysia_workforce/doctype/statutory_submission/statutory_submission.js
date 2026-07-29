frappe.ui.form.on("Statutory Submission", {
	refresh(frm) {
		if (frm.is_new()) return;

		if (!["Submitted", "Accepted", "Paid", "Reconciled"].includes(frm.doc.status)) {
			if (["Monthly PCB", "EPF Form A", "SOCSO EIS Combined"].includes(frm.doc.submission_type)) {
				frm.add_custom_button(__("Load from Payroll"), () => callDoc(frm, "load_from_payroll"), __("Submission"));
			}
			frm.add_custom_button(__("Generate File"), () => callDoc(frm, "generate_file"), __("Submission"));
		}

		if (frm.doc.portal_url && ["Ready for Portal", "Generated", "Rejected"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Open Official Portal"), () => window.open(frm.doc.portal_url, "_blank", "noopener"), __("Submission"));
		}

		if (["Ready for Portal", "Generated", "Rejected"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Mark Submitted"), () => {
				frappe.prompt(
					[{ fieldname: "external_reference", label: __("External Reference"), fieldtype: "Data", reqd: 1 }],
					(values) => callDoc(frm, "mark_submitted", values),
					__("Submission Reference"),
				);
			}, __("Status"));
		}
		if (frm.doc.status === "Submitted") {
			frm.add_custom_button(__("Mark Accepted"), () => callDoc(frm, "mark_accepted"), __("Status"));
			frm.add_custom_button(__("Mark Rejected"), () => {
				frappe.prompt(
					[{ fieldname: "reason", label: __("Rejection Reason"), fieldtype: "Small Text", reqd: 1 }],
					(values) => callDoc(frm, "mark_rejected", values),
					__("Rejection"),
				);
			}, __("Status"));
		}
		if (["Submitted", "Accepted", "Paid"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Record Payment"), () => {
				frappe.prompt(
					[
						{ fieldname: "payment_reference", label: __("Payment Reference"), fieldtype: "Data", reqd: 1 },
						{ fieldname: "paid_amount", label: __("Paid Amount"), fieldtype: "Currency", reqd: 1, default: frm.doc.payable_total },
					],
					(values) => callDoc(frm, "mark_paid", values),
					__("Authority Payment"),
				);
			}, __("Status"));
		}
		if (frm.doc.status === "Paid") {
			frm.add_custom_button(__("Reconcile"), () => callDoc(frm, "reconcile"), __("Status"));
		}
	},
});

function callDoc(frm, method, args = {}) {
	return frm.call(method, args).then(() => frm.reload_doc());
}
