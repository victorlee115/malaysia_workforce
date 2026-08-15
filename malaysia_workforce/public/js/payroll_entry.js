frappe.ui.form.on("Payroll Entry", {
	refresh(frm) {
		if (!frm.doc.company || frm.is_new() || !frm.perm?.[0]?.read) return;
		frm.add_custom_button(__("Check Statutory Setup"), () => {
			frappe.call({
				method: "malaysia_workforce.payroll.events.check_readiness",
				args: { payroll_entry: frm.doc.name },
				freeze: true,
				freeze_message: __("Checking employee and payroll setup…"),
				callback: (response) => {
					const companyIssues = response.message?.company_issues || [];
					const blocked = (response.message?.employees || []).filter((row) => row.issues.length);
					if (!companyIssues.length && !blocked.length) {
						frappe.show_alert({ message: __("Statutory setup is ready"), indicator: "green" });
						return;
					}
					const companyItems = companyIssues.map((issue) =>
						`<li><strong>${__("Company")}</strong>: ${frappe.utils.escape_html(issue)}</li>`
					);
					const employeeItems = blocked.map((row) =>
						`<li><a href="/app/employee/${encodeURIComponent(row.employee)}">${frappe.utils.escape_html(row.employee)}</a>: ${frappe.utils.escape_html(row.issues.join(" "))}</li>`
					);
					frappe.msgprint({
						title: __("Setup needs attention"),
						indicator: "orange",
						message: `<ul>${companyItems.concat(employeeItems).join("")}</ul>`,
					});
				},
			});
		});
	},
});
