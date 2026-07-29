from __future__ import annotations

import frappe
from frappe.utils import add_to_date, now_datetime


def close_expired_rosters():
	for name in frappe.get_all(
		"Casual Roster",
		filters={"status": "Open for Applications", "application_closes": ["<=", now_datetime()]},
		pluck="name",
	):
		frappe.db.set_value("Casual Roster", name, "status", "Applications Closed", update_modified=True)


def process_expired_standby_offers():
	for name in frappe.get_all(
		"Roster Standby",
		filters={"offer_status": "Offered", "offer_expires_on": ["<=", now_datetime()]},
		pluck="name",
	):
		frappe.db.set_value("Roster Standby", name, "offer_status", "Expired", update_modified=True)


def send_application_reminders():
	"""Create one in-app reminder per employee and roster near the closing deadline.

	This intentionally avoids email by default; deployments can attach a Notification
	or Notification Settings rule to Notification Log if email/push is desired.
	"""
	hours = int(frappe.db.get_single_value("Malaysia Workforce Settings", "application_reminder_hours") or 24)
	cutoff = add_to_date(now_datetime(), hours=hours)
	rosters = frappe.get_all(
		"Casual Roster",
		filters={
			"status": "Open for Applications",
			"application_closes": ["between", [now_datetime(), cutoff]],
		},
		fields=["name", "roster_title", "company", "application_opens", "application_closes"],
	)
	if not rosters:
		return
	for employee in frappe.get_all(
		"Employee",
		filters={"status": "Active", "custom_roster_enabled": 1, "user_id": ["is", "set"]},
		fields=["name", "user_id", "company"],
		limit_page_length=10000,
	):
		for roster in rosters:
			if roster.company != employee.company:
				continue
			if roster.application_opens and roster.application_opens > now_datetime():
				continue
			if frappe.db.exists("Roster Application", {"roster": roster.name, "employee": employee.name, "status": ["!=", "Withdrawn"]}):
				continue
			key = f"mw-roster-reminder:{roster.name}:{employee.name}"
			if frappe.cache.get_value(key):
				continue
			frappe.get_doc(
				{
					"doctype": "Notification Log",
					"subject": f"Roster applications close soon: {roster.roster_title}",
					"for_user": employee.user_id,
					"type": "Alert",
					"document_type": "Casual Roster",
					"document_name": roster.name,
					"from_user": "Administrator",
				}
			).insert(ignore_permissions=True)
			frappe.cache.set_value(key, 1, expires_in_sec=max(hours * 3600, 3600))
