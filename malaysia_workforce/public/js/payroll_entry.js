frappe.ui.form.on("Payroll Entry", {
	refresh(frm) {
		if (!frm.doc.company || frm.is_new() || !frm.perm?.[0]?.write) return;
		frm.add_custom_button(__("Check Statutory Setup"), () => {
			frappe.call({
				method: "malaysia_workforce.payroll.events.check_readiness",
				args: { payroll_entry: frm.doc.name },
				freeze: true,
				freeze_message: __("Checking employee and payroll setup…"),
				callback: (response) => {
					const companyIssues = response.message?.company_issues || [];
					const employees = response.message?.employees || [];
					const blocked = employees.filter((row) => row.issues.length);
					const noted = employees.filter((row) => !row.issues.length && row.notes?.length);
					if (!companyIssues.length && !blocked.length && !noted.length) {
						frappe.msgprint({
							title: __("Statutory setup is ready"),
							indicator: "green",
							message: __("Company and employee statutory setup for this payroll period is complete. Review the Salary Slips before submitting."),
						});
						return;
					}
					const companyItems = companyIssues.map((issue) =>
						`<li><strong>${__("Company")}</strong>: ${frappe.utils.escape_html(issue)}</li>`
					);
					const employeeItems = blocked.map((row) =>
						`<li><a href="/app/employee/${encodeURIComponent(row.employee)}">${frappe.utils.escape_html(row.employee)}</a> (${frappe.utils.escape_html(row.profile)}): ${frappe.utils.escape_html(row.issues.join(" "))}</li>`
					);
					const noteItems = noted.map((row) =>
						`<li><a href="/app/employee/${encodeURIComponent(row.employee)}">${frappe.utils.escape_html(row.employee)}</a> (${frappe.utils.escape_html(row.profile)}): ${frappe.utils.escape_html(row.notes.join(" "))}</li>`
					);
					if (!companyIssues.length && !blocked.length) {
						frappe.msgprint({
							title: __("Worth reviewing"),
							indicator: "blue",
							message: `<ul>${noteItems.join("")}</ul>`,
						});
						return;
					}
					const reviewSection = noteItems.length
						? `<p><strong>${__("Worth reviewing")}:</strong></p><ul>${noteItems.join("")}</ul>`
						: "";
					frappe.msgprint({
						title: __("Setup needs attention"),
						indicator: "orange",
						message: `<ul>${companyItems.concat(employeeItems).join("")}</ul>${reviewSection}`,
					});
				},
			});
		});
	},
});
