(() => {
	const root = document.getElementById("mw-portal");
	if (!root) return;
	const content = document.getElementById("mw-content");
	let dashboard = null;
	let activeTab = "home";
	let selectedRoster = null;
	const escape = (value) => {
		const node = document.createElement("div");
		node.textContent = value == null ? "" : String(value);
		return node.innerHTML;
	};
	const time = (value) => (value ? String(value).slice(0, 5) : "");
	const call = (method, args = {}) => frappe.call({ method, args, freeze: false }).then((response) => response.message);
	const modal = (action) => {
		const element = document.getElementById("mw-apply-modal");
		if (window.jQuery && typeof window.jQuery.fn?.modal === "function") {
			window.jQuery(element).modal(action);
			return;
		}
		if (window.bootstrap?.Modal) {
			const instance = window.bootstrap.Modal.getOrCreateInstance(element);
			instance[action]();
			return;
		}
		throw new Error(__("The page modal library is unavailable. Refresh the page and try again."));
	};

	document.querySelectorAll(".mw-tabs button").forEach((button) =>
		button.addEventListener("click", () => {
			document.querySelectorAll(".mw-tabs button").forEach((tab) => tab.classList.toggle("active", tab === button));
			activeTab = button.dataset.tab;
			render();
		}),
	);
	document.getElementById("mw-refresh").addEventListener("click", load);

	async function load() {
		content.innerHTML = `<div class="mw-loading">${__("Loading…")}</div>`;
		try {
			dashboard = await call("malaysia_workforce.api.roster.get_employee_dashboard");
			const count = dashboard.pending_offers?.length || 0;
			const badge = document.getElementById("mw-offer-count");
			badge.hidden = count === 0;
			badge.textContent = count;
			render();
		} catch (error) {
			content.innerHTML = `<div class="mw-card text-danger">${escape(error.message || error)}</div>`;
		}
	}

	function render() {
		if (!dashboard) return;
		if (activeTab === "home") renderHome();
		else if (activeTab === "offers") renderOffers();
		else if (activeTab === "open") renderOpen();
		else if (activeTab === "applications") renderApplications();
		else renderShifts();
	}

	function renderHome() {
		const next = dashboard.confirmed[0];
		const action = dashboard.pending_offers?.[0];
		content.innerHTML = `<div class="mw-clock"><button class="btn btn-success" id="mw-clock-in">${__("Clock In")}</button><button class="btn btn-outline-danger" id="mw-clock-out">${__("Clock Out")}</button></div>
		${action ? `<article class="mw-card mw-action-card"><span class="mw-status">${__("Action required")}</span><h3>${__("Confirm your exact hours")}</h3><p>${escape(action.work_date)} · ${time(action.selected_from)}–${time(action.selected_until)} · ${escape(action.assigned_role || "")}</p><div class="mw-actions"><button class="btn btn-primary mw-open-offers">${__("Review offer")}</button></div></article>` : ""}
		${next ? shiftCard(next, true) : `<div class="mw-empty">${__("No upcoming confirmed shifts.")}</div>`}`;
		document.getElementById("mw-clock-in").onclick = () => clock("IN");
		document.getElementById("mw-clock-out").onclick = () => clock("OUT");
		const offersButton = content.querySelector(".mw-open-offers");
		if (offersButton) {
			offersButton.onclick = () => {
				activeTab = "offers";
				document.querySelectorAll(".mw-tabs button").forEach((button) => button.classList.toggle("active", button.dataset.tab === "offers"));
				renderOffers();
			};
		}
	}

	async function clock(logType) {
		const position = await getPosition().catch(() => null);
		try {
			const result = await call("malaysia_workforce.api.attendance.clock", {
				log_type: logType,
				latitude: position?.coords.latitude,
				longitude: position?.coords.longitude,
			});
			frappe.show_alert({ message: `${__("Recorded")} ${logType}: ${result.time || ""}`, indicator: "green" });
		} catch (error) {
			frappe.msgprint({ title: __("Unable to record attendance"), message: escape(error.message || String(error)), indicator: "red" });
		}
	}

	function getPosition() {
		return new Promise((resolve, reject) =>
			navigator.geolocation
				? navigator.geolocation.getCurrentPosition(resolve, reject, { enableHighAccuracy: false, timeout: 6000 })
				: reject(new Error(__("Geolocation is not available."))),
		);
	}

	function renderOffers() {
		const offers = dashboard.pending_offers || [];
		content.innerHTML = offers.length
			? offers
					.map(
						(row) => `<article class="mw-card mw-action-card"><span class="mw-status">${__("Confirmation required")}</span><h3>${escape(row.assigned_role || __("Roster shift"))}</h3><div class="mw-meta"><span>${escape(row.work_date)}</span><span>${time(row.selected_from)}–${time(row.selected_until)}</span><span>${escape(row.shift_location || "")}</span><span>RM ${Number(row.hourly_rate || 0).toFixed(2)}/${__("hour")}</span></div><p class="mw-help">${__("These exact hours must be confirmed before the manager can publish the roster.")}</p><div class="mw-actions"><button class="btn btn-primary mw-accept-offer" data-selection="${escape(row.name)}">${__("Accept")}</button><button class="btn btn-outline-danger mw-decline-offer" data-selection="${escape(row.name)}">${__("Decline")}</button></div></article>`,
					)
					.join("")
			: `<div class="mw-empty">${__("You have no offers waiting for confirmation.")}</div>`;
		content.querySelectorAll(".mw-accept-offer").forEach((button) => {
			button.onclick = () => respondToOffer(button.dataset.selection, true);
		});
		content.querySelectorAll(".mw-decline-offer").forEach((button) => {
			button.onclick = () =>
				frappe.confirm(__("Decline these working hours? The manager may send a different offer."), () =>
					respondToOffer(button.dataset.selection, false),
				);
		});
	}

	async function respondToOffer(selection, accept) {
		try {
			await call("malaysia_workforce.api.roster.respond_to_selection", { selection, accept: accept ? 1 : 0 });
			frappe.show_alert({ message: accept ? __("Hours accepted") : __("Offer declined"), indicator: accept ? "green" : "orange" });
			await load();
		} catch (error) {
			frappe.msgprint({ title: __("Unable to update offer"), message: escape(error.message || String(error)), indicator: "red" });
		}
	}

	function renderOpen() {
		content.innerHTML = dashboard.open_rosters.length
			? dashboard.open_rosters
					.map(
						(roster) => `<article class="mw-card"><h3>${escape(roster.roster_title)}</h3><div class="mw-meta"><span>${escape(roster.start_date)} – ${escape(roster.end_date)}</span><span>${__("Closes")}: ${escape(roster.application_closes || "—")}</span></div><div class="mw-actions"><button class="btn btn-primary mw-apply" data-roster="${escape(roster.name)}">${__("Specify my hours")}</button></div></article>`,
					)
					.join("")
			: `<div class="mw-empty">${__("No rosters are open right now.")}</div>`;
		content.querySelectorAll(".mw-apply").forEach((button) => {
			button.onclick = () => openApplication(button.dataset.roster);
		});
	}

	function renderApplications() {
		content.innerHTML = dashboard.applications.length
			? dashboard.applications
					.map(
						(app) => `<article class="mw-card"><span class="mw-status">${escape(app.status)}</span><h3>${escape(app.roster)}</h3><div class="mw-meta"><span>${__("Applied")}: ${escape(app.applied_on)}</span><span>${escape(app.preferred_role || "")}</span></div>${app.status === "Applied" ? `<div class="mw-actions"><button class="btn btn-outline-danger mw-withdraw" data-name="${escape(app.name)}">${__("Withdraw")}</button></div>` : ""}</article>`,
					)
					.join("")
			: `<div class="mw-empty">${__("You have no active applications.")}</div>`;
		content.querySelectorAll(".mw-withdraw").forEach((button) => {
			button.onclick = async () => {
				await call("malaysia_workforce.api.roster.withdraw_application", { application: button.dataset.name });
				await load();
			};
		});
	}

	function renderShifts() {
		content.innerHTML = dashboard.confirmed.length
			? dashboard.confirmed.map((row) => shiftCard(row)).join("")
			: `<div class="mw-empty">${__("No confirmed shifts.")}</div>`;
	}

	function shiftCard(row, next = false) {
		return `<article class="mw-card">${next ? `<span class="mw-status">${__("Next shift")}</span>` : ""}<h3>${escape(row.assigned_role || __("Roster shift"))}</h3><div class="mw-meta"><span>${escape(row.work_date)}</span><span>${time(row.selected_from)}–${time(row.selected_until)}</span><span>${escape(row.shift_location || "")}</span><span>RM ${Number(row.hourly_rate || 0).toFixed(2)}/${__("hour")}</span></div></article>`;
	}

	async function openApplication(roster) {
		selectedRoster = await call("malaysia_workforce.api.roster.get_roster_details", { roster });
		const requirements = selectedRoster.roster.coverage_requirements || [];
		const dates = [...new Set(requirements.map((row) => row.work_date))];
		const roles = [...new Set(requirements.map((row) => row.role).filter(Boolean))];
		document.getElementById("mw-apply-body").innerHTML = `<p>${__("Enter one or more exact windows. The manager can only assign hours inside them unless they record an override.")}</p><div id="mw-windows"></div><button class="btn btn-sm btn-outline-primary" id="mw-add-window">+ ${__("Add another time")}</button><hr><div class="row"><div class="col-sm-6"><label for="mw-preferred-role">${__("Preferred role")}</label><select class="form-control" id="mw-preferred-role"><option value="">${__("No preference")}</option>${roles.map((role) => `<option value="${escape(role)}">${escape(role)}</option>`).join("")}</select></div><div class="col-sm-6"><label for="mw-commitment">${__("After the manager selects hours")}</label><select class="form-control" id="mw-commitment"><option value="Manager may assign any hours inside my availability">${__("Confirm automatically if inside my availability")}</option><option value="Ask me to confirm exact hours">${__("Ask me to confirm the exact hours")}</option></select></div></div><div class="row mt-3"><div class="col-sm-6"><label for="mw-min-hours">${__("Minimum shift hours")}</label><input class="form-control" id="mw-min-hours" type="number" min="0.5" step="0.5" value="2"></div><div class="col-sm-6"><label for="mw-max-hours">${__("Maximum total hours")}</label><input class="form-control" id="mw-max-hours" type="number" min="0.5" step="0.5" placeholder="${__("No maximum")}"></div></div><div class="form-check mt-3"><input class="form-check-input" type="checkbox" id="mw-split" ${selectedRoster.allow_split_shifts ? "" : "disabled"}><label class="form-check-label" for="mw-split">${__("I accept split shifts")}</label>${selectedRoster.allow_split_shifts ? "" : `<small class="form-text text-muted">${__("Split shifts are unavailable until HR enables multiple same-date Shift Assignments.")}</small>`}</div>`;
		const addWindow = () => {
			const row = document.createElement("div");
			row.className = "mw-window-row";
			row.innerHTML = `<div><label>${__("Date")}</label><select class="mw-date">${dates.map((date) => `<option>${escape(date)}</option>`).join("")}</select></div><div><label>${__("From")}</label><input class="mw-from" type="time" required></div><div class="mw-preference"><label>${__("Until / preference")}</label><input class="mw-until" type="time" required><select class="mw-pref mt-1"><option>Preferred</option><option selected>Available</option><option>Available if Needed</option></select></div><button class="mw-remove" type="button" aria-label="${__("Remove")}">×</button>`;
			row.querySelector(".mw-remove").onclick = () => row.remove();
			document.getElementById("mw-windows").appendChild(row);
		};
		document.getElementById("mw-add-window").onclick = addWindow;
		addWindow();
		modal("show");
	}

	document.getElementById("mw-submit-application").onclick = async () => {
		const windows = [...document.querySelectorAll(".mw-window-row")].map((row) => ({
			work_date: row.querySelector(".mw-date").value,
			available_from: row.querySelector(".mw-from").value,
			available_until: row.querySelector(".mw-until").value,
			preference: row.querySelector(".mw-pref").value,
		}));
		if (!windows.length || windows.some((row) => !row.available_from || !row.available_until)) {
			frappe.msgprint(__("Complete at least one availability window."));
			return;
		}
		const maximum = document.getElementById("mw-max-hours").value;
		await call("malaysia_workforce.api.roster.submit_application", {
			roster: selectedRoster.roster.name,
			availability_windows: windows,
			preferred_role: document.getElementById("mw-preferred-role").value || null,
			minimum_shift_hours: document.getElementById("mw-min-hours").value || null,
			maximum_hours: maximum || null,
			split_shifts_allowed: document.getElementById("mw-split").checked ? 1 : 0,
			commitment_type: document.getElementById("mw-commitment").value,
		});
		modal("hide");
		await load();
	};

	load();
})();
