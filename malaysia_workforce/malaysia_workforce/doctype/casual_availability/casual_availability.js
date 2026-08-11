frappe.ui.form.on("Casual Availability", {
	refresh(frm) {
		if (!frm.is_new() || frm.doc.docstatus !== 0) return;
		frm.add_custom_button(__("Copy Previous Cycle"), () => {
			frappe.call({
				method: "malaysia_workforce.malaysia_workforce.doctype.casual_availability.casual_availability.previous_availability_windows",
				args: { cycle_start: frm.doc.cycle_start },
				callback: ({ message }) => {
					if (!message || !message.length) {
						frappe.show_alert({ message: __("No submitted availability was found for the previous cycle."), indicator: "orange" });
						return;
					}
					frappe.confirm(__("Replace the current windows with the previous cycle's hours?"), () => {
						frm.clear_table("availability_windows");
						message.forEach((row) => frm.add_child("availability_windows", row));
						frm.refresh_field("availability_windows");
					});
				},
			});
		});
	},
});
