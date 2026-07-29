frappe.pages["casual-roster-planner"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Casual Roster Planner"),
		single_column: true,
	});
	page.main.html(`<div class="mw-planner">
		<div class="mw-toolbar"><div class="mw-roster-field"></div><button class="btn btn-primary mw-refresh">${__("Load")}</button></div>
		<div class="mw-content"><div class="text-muted">${__("Select a roster.")}</div></div>
	</div>`);
	const rosterControl = frappe.ui.form.make_control({
		parent: page.main.find(".mw-roster-field"),
		df: { fieldtype: "Link", options: "Casual Roster", label: __("Roster"), fieldname: "roster" },
		render_input: true,
	});
	const route = frappe.get_route();
	const initial = route.length > 1 && route[1] !== "casual-roster-planner" ? route[1] : null;
	if (initial) rosterControl.set_value(initial);
	page.main.find(".mw-refresh").on("click", () => loadRoster(page, rosterControl.get_value()));
	if (initial) loadRoster(page, initial);
};

const escapeHTML = (value) => frappe.utils.escape_html(value == null ? "" : String(value));
const formatTime = (value) => (value ? String(value).slice(0, 5) : "");
const normalizeTime = (value) => (value ? String(value).slice(0, 8) : "");

async function loadRoster(page, roster) {
	if (!roster) return;
	page.main.find(".mw-content").html(`<div class="text-muted">${__("Loading…")}</div>`);
	const { message } = await frappe.call("malaysia_workforce.api.roster.manager_roster", { roster });
	renderPlanner(page, message);
}

function requirementLabel(row) {
	return `${row.idx} · ${row.work_date} · ${row.role} · ${formatTime(row.start_time)}–${formatTime(row.end_time)}`;
}

function isActiveSelection(row) {
	return Number(row.docstatus) < 2 && row.status !== "Declined";
}

function selectionCount(data, requirement) {
	return data.selections.filter(
		(row) => Number(row.coverage_requirement_idx) === Number(requirement.idx) && isActiveSelection(row),
	).length;
}

function renderPlanner(page, data) {
	const gaps = data.coverage.reduce((total, row) => total + Number(row.gap || 0), 0);
	const requirements = data.roster.coverage_requirements || [];
	const requirementRows = requirements
		.map((row) => {
			const selected = selectionCount(data, row);
			const gap = Math.max(Number(row.required_headcount || 0) - selected, 0);
			return `<tr>
				<td>${row.idx}</td><td>${escapeHTML(row.work_date)}</td><td>${escapeHTML(row.role)}</td>
				<td>${formatTime(row.start_time)}–${formatTime(row.end_time)}</td>
				<td>${row.required_headcount}</td><td>${selected}</td><td class="${gap ? "mw-gap" : ""}">${gap}</td>
				<td><button class="btn btn-xs btn-default mw-recommend" data-idx="${row.idx}">${__("Recommend")}</button></td>
			</tr>`;
		})
		.join("");
	const coverageRows = data.coverage
		.map(
			(row) => `<tr><td>${escapeHTML(row.work_date)}</td><td>${escapeHTML(row.role)}</td>
			<td>${formatTime(row.start)}–${formatTime(row.end)}</td><td>${row.required}</td><td>${row.selected}</td>
			<td class="${row.gap ? "mw-gap" : ""}">${row.gap}</td></tr>`,
		)
		.join("");
	const applications = data.applications
		.map((app) => {
			const windows = (app.availability_windows || [])
				.map(
					(window) => `<span class="mw-window">${escapeHTML(window.work_date)} ${formatTime(window.available_from)}–${formatTime(window.available_until)} · ${escapeHTML(window.preference)}</span>`,
				)
				.join("");
			return `<tr>
				<td><strong>${escapeHTML(app.employee_name)}</strong><br><small>${escapeHTML(app.employee)}</small></td>
				<td>${windows || "—"}</td><td>${escapeHTML(app.preferred_role || "—")}</td><td>${escapeHTML(app.status)}</td>
				<td><button class="btn btn-xs btn-primary mw-select" data-application="${escapeHTML(app.name)}">${__("Select Hours")}</button></td>
			</tr>`;
		})
		.join("");
	page.main.find(".mw-content").html(`
		<div class="mw-summary-grid">
			<div class="mw-stat"><span>${__("Applications")}</span><strong>${data.applications.length}</strong></div>
			<div class="mw-stat"><span>${__("Selections")}</span><strong>${data.selections.filter(isActiveSelection).length}</strong></div>
			<div class="mw-stat"><span>${__("Coverage gaps")}</span><strong class="${gaps ? "mw-gap" : ""}">${gaps}</strong></div>
		</div>
		<div class="mw-toolbar mw-manager-actions">
			<span class="mw-status">${escapeHTML(data.roster.status)}</span>
			${data.roster.status === "Open for Applications" ? `<button class="btn btn-default mw-close-applications">${__("Close Applications")}</button>` : ""}
			${!["Published", "In Progress", "Completed", "Payroll Ready", "Closed"].includes(data.roster.status) ? `<button class="btn btn-primary mw-publish-roster">${__("Publish Roster")}</button>` : ""}
		</div>
		<h4>${__("Coverage requirements")}</h4>
		<div class="mw-coverage"><table class="mw-table"><thead><tr><th>#</th><th>${__("Date")}</th><th>${__("Role")}</th><th>${__("Hours")}</th><th>${__("Needed")}</th><th>${__("Selected")}</th><th>${__("Gap")}</th><th></th></tr></thead><tbody>${requirementRows}</tbody></table></div>
		<h4>${__("Role-aware coverage timeline")}</h4>
		<div class="mw-coverage"><table class="mw-table"><thead><tr><th>${__("Date")}</th><th>${__("Role")}</th><th>${__("Hours")}</th><th>${__("Required")}</th><th>${__("Selected")}</th><th>${__("Gap")}</th></tr></thead><tbody>${coverageRows}</tbody></table></div>
		<h4>${__("Applicants")}</h4>
		<div class="mw-coverage"><table class="mw-table"><thead><tr><th>${__("Employee")}</th><th>${__("Available hours")}</th><th>${__("Preferred role")}</th><th>${__("Status")}</th><th></th></tr></thead><tbody>${applications || `<tr><td colspan="5">${__("No applications yet.")}</td></tr>`}</tbody></table></div>
	`);
	page.main.find(".mw-select").on("click", (event) =>
		openSelectionDialog(data, event.currentTarget.dataset.application, page),
	);
	page.main.find(".mw-recommend").on("click", (event) =>
		showRecommendations(data, Number(event.currentTarget.dataset.idx), page),
	);
	page.main.find(".mw-close-applications").on("click", async () => {
		await frappe.call({
			method: "malaysia_workforce.api.roster.close_applications",
			args: { roster: data.roster.name },
			freeze: true,
		});
		loadRoster(page, data.roster.name);
	});
	page.main.find(".mw-publish-roster").on("click", () => {
		const publish = async (allowGaps) => {
			await frappe.call({
				method: "malaysia_workforce.api.roster.publish_roster",
				args: { roster: data.roster.name, allow_gaps: allowGaps ? 1 : 0 },
				freeze: true,
			});
			loadRoster(page, data.roster.name);
		};
		if (gaps > 0) {
			frappe.confirm(
				__("This roster still has uncovered role/time slots. Publish it anyway?"),
				() => publish(true),
			);
		} else {
			publish(false);
		}
	});
}

function timeToMinutes(value) {
	const [hours, minutes] = String(value || "00:00").split(":").map(Number);
	return hours * 60 + minutes;
}

function minutesToTime(value) {
	const normalised = ((value % 1440) + 1440) % 1440;
	return `${String(Math.floor(normalised / 60)).padStart(2, "0")}:${String(normalised % 60).padStart(2, "0")}:00`;
}

function interval(startValue, endValue) {
	const start = timeToMinutes(startValue);
	let end = timeToMinutes(endValue);
	if (end <= start) end += 1440;
	return { start, end };
}

function intersection(applicationWindow, requirement) {
	if (String(applicationWindow.work_date) !== String(requirement.work_date)) return null;
	const available = interval(applicationWindow.available_from, applicationWindow.available_until);
	const required = interval(requirement.start_time, requirement.end_time);
	const start = Math.max(available.start, required.start);
	const end = Math.min(available.end, required.end);
	return end > start ? { start, end, preference: applicationWindow.preference } : null;
}

function defaultRequirement(data, application) {
	for (const requirement of data.roster.coverage_requirements || []) {
		if ((application.availability_windows || []).some((window) => intersection(window, requirement))) return requirement;
	}
	return (data.roster.coverage_requirements || [])[0];
}

function defaultWindow(application, requirement) {
	const overlaps = (application.availability_windows || [])
		.map((window) => intersection(window, requirement))
		.filter(Boolean)
		.sort((a, b) => (a.preference === "Preferred" ? -1 : 0) - (b.preference === "Preferred" ? -1 : 0));
	if (!overlaps.length) {
		return { from: requirement.start_time, until: requirement.end_time };
	}
	return { from: minutesToTime(overlaps[0].start), until: minutesToTime(overlaps[0].end) };
}

function openSelectionDialog(data, applicationName, page, initialRequirementIdx = null) {
	const application = data.applications.find((row) => row.name === applicationName);
	const requirements = data.roster.coverage_requirements || [];
	const initial =
		requirements.find((row) => Number(row.idx) === Number(initialRequirementIdx)) ||
		defaultRequirement(data, application);
	if (!application || !initial) {
		frappe.msgprint(__("No application or coverage requirement is available."));
		return;
	}
	const initialWindow = defaultWindow(application, initial);
	const optionLines = requirements.map(requirementLabel).join("\n");
	const dialog = new frappe.ui.Dialog({
		title: __("Select exact working hours"),
		fields: [
			{
				fieldname: "coverage_requirement",
				fieldtype: "Select",
				label: __("Coverage Requirement"),
				reqd: 1,
				options: optionLines,
				default: requirementLabel(initial),
			},
			{ fieldname: "selected_from", fieldtype: "Time", label: __("From"), reqd: 1, default: initialWindow.from },
			{ fieldname: "selected_until", fieldtype: "Time", label: __("Until"), reqd: 1, default: initialWindow.until },
			{ fieldname: "hourly_rate", fieldtype: "Currency", label: __("Hourly Rate"), default: initial.hourly_rate },
			{ fieldname: "outside_availability_override", fieldtype: "Check", label: __("Assign outside submitted availability") },
			{ fieldname: "override_reason", fieldtype: "Small Text", label: __("Override Reason"), depends_on: "outside_availability_override", mandatory_depends_on: "outside_availability_override" },
		],
		primary_action_label: __("Save Selection"),
		async primary_action(values) {
			const idx = Number(String(values.coverage_requirement).split("·")[0].trim());
			await frappe.call({
				method: "malaysia_workforce.api.roster.select_employee",
				args: {
					application: applicationName,
					coverage_requirement_idx: idx,
					selected_from: values.selected_from,
					selected_until: values.selected_until,
					hourly_rate: values.hourly_rate,
					outside_availability_override: values.outside_availability_override,
					override_reason: values.override_reason,
				},
				freeze: true,
			});
			dialog.hide();
			loadRoster(page, data.roster.name);
		},
	});
	dialog.fields_dict.coverage_requirement.$input.on("change", () => {
		const selectedValue = dialog.get_value("coverage_requirement");
		const idx = Number(String(selectedValue).split("·")[0].trim());
		const requirement = requirements.find((row) => Number(row.idx) === idx);
		if (!requirement) return;
		const window = defaultWindow(application, requirement);
		dialog.set_value("selected_from", normalizeTime(window.from));
		dialog.set_value("selected_until", normalizeTime(window.until));
		dialog.set_value("hourly_rate", requirement.hourly_rate || 0);
	});
	dialog.show();
}

async function showRecommendations(data, requirementIdx, page) {
	const { message } = await frappe.call("malaysia_workforce.api.roster.recommend", {
		roster: data.roster.name,
		requirement_idx: requirementIdx,
	});
	if (!message || !message.length) {
		frappe.msgprint(__("No additional eligible applicants cover this entire requirement."));
		return;
	}
	const rows = message
		.map(
			(row) => `<tr><td>${escapeHTML(row.employee_name)}<br><small>${escapeHTML(row.employee)}</small></td><td>${formatTime(row.selected_from)}–${formatTime(row.selected_until)}</td><td>RM ${Number(row.hourly_rate || 0).toFixed(2)}</td><td>${(row.reasons || []).map(escapeHTML).join("<br>")}</td><td><button class="btn btn-xs btn-primary mw-use-recommendation" data-employee="${escapeHTML(row.employee)}">${__("Select")}</button></td></tr>`,
		)
		.join("");
	const dialog = new frappe.ui.Dialog({ title: __("Recommended applicants"), size: "large" });
	dialog.$body.html(`<table class="mw-table"><thead><tr><th>${__("Employee")}</th><th>${__("Hours")}</th><th>${__("Rate")}</th><th>${__("Reasons")}</th><th></th></tr></thead><tbody>${rows}</tbody></table>`);
	dialog.$body.find(".mw-use-recommendation").on("click", (event) => {
		const employee = event.currentTarget.dataset.employee;
		const application = data.applications.find((row) => row.employee === employee);
		dialog.hide();
		if (application) openSelectionDialog(data, application.name, page, requirementIdx);
	});
	dialog.show();
}
