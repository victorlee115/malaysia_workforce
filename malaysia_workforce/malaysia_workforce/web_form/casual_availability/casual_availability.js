frappe.ready(() => {
	const setupAvailabilityForm = async () => {
		if (frappe.web_form.malaysia_workforce_ready) return;
		frappe.web_form.malaysia_workforce_ready = true;

		if (frappe.web_form.is_new) {
			const { message } = await frappe.call({
				method: "malaysia_workforce.malaysia_workforce.doctype.casual_availability.casual_availability.availability_context",
			});
			if (message) {
				frappe.web_form.set_value("cycle_start", message.cycle_start);
				frappe.web_form.set_value("cycle_end", message.cycle_end);
			}
		}
		if (!frappe.web_form.is_new || document.querySelector(".mw-copy-availability")) return;
		const button = $(`<button type="button" class="btn btn-default btn-sm mw-copy-availability">${__("Copy Previous Cycle")}</button>`);
		button.on("click", async () => {
			const cycleStart = frappe.web_form.get_value("cycle_start");
			const { message } = await frappe.call({
				method: "malaysia_workforce.malaysia_workforce.doctype.casual_availability.casual_availability.previous_availability_windows",
				args: { cycle_start: cycleStart },
			});
			if (!message || !message.length) {
				frappe.msgprint(__("No submitted availability was found for the previous cycle."));
				return;
			}
			frappe.confirm(__("Replace the current windows with the previous cycle's hours?"), () => {
				const table = frappe.web_form.fields_dict.availability_windows;
				table.df.data = message.map((row, index) => ({
					...row,
					idx: index + 1,
				}));
				table.grid.refresh();
				frappe.web_form.make_form_dirty();
			});
		});
		button.prependTo(".web-form-footer .left-area");
	};

	frappe.web_form.after_load = setupAvailabilityForm;
	// The standard web-form bundle registers its ready handler before this
	// standard-form script. Run once immediately when the form is already made.
	if (frappe.web_form.doc && frappe.web_form.fields_dict) {
		setupAvailabilityForm();
	}
});
