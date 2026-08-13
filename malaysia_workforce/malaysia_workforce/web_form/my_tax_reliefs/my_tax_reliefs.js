frappe.ready(() => {
	const original_handle_success = frappe.web_form.handle_success.bind(frappe.web_form);

	frappe.web_form.handle_success = (data) => {
		frappe.call({
			method: "malaysia_workforce.permissions.send_tax_declaration_for_review",
			args: { doctype: "Malaysia Tax Declaration TP1", name: data.name },
			freeze: true,
			freeze_message: __("Sending your declaration for review…"),
			callback: ({ message }) => {
				if (message?.workflow_state === "Pending Review") original_handle_success(data);
			},
		});
	};
});
