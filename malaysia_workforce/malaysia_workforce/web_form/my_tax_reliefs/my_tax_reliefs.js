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

	load_relief_catalog();
	frappe.web_form.on("tax_year", () => load_relief_catalog());
});

// Web Form Table fields do not fire a per-row change event the way Desk's
// frappe.ui.form.on(child_doctype, {fieldname(frm, cdt, cdn) {...}}) does, so relief codes
// are explained with a static legend above the table instead of live per-row annotation.
function load_relief_catalog() {
	const tax_year = frappe.web_form.doc.tax_year;
	if (!tax_year) return;
	frappe.call({
		method: "malaysia_workforce.malaysia_workforce.doctype.malaysia_tax_declaration_tp1.malaysia_tax_declaration_tp1.relief_catalog",
		args: { tax_year },
		callback: ({ message }) => render_relief_legend(message || {}),
	});
}

function render_relief_legend(catalog) {
	const field = frappe.web_form.fields_dict["relief_claims"];
	if (!field) return;
	const $wrapper = $(field.wrapper);
	let $legend = $wrapper.find(".malaysia-relief-legend");
	if (!$legend.length) {
		$legend = $('<div class="malaysia-relief-legend text-muted small" style="margin-bottom: 10px;"></div>');
		$wrapper.prepend($legend);
	}
	const rows = Object.entries(catalog);
	if (!rows.length) {
		$legend.empty();
		return;
	}
	$legend.html(
		`<strong>${__("Relief codes")}</strong>` +
			`<ul style="margin: 6px 0 0; padding-left: 1.2em;">` +
			rows
				.map(
					([code, label]) =>
						`<li><strong>${frappe.utils.escape_html(code)}</strong> — ${frappe.utils.escape_html(label)}</li>`
				)
				.join("") +
			`</ul>`
	);
}
