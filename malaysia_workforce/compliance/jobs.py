from __future__ import annotations

import frappe
from frappe.utils import add_days, getdate, today


def refresh_obligations():
	"""Create missing CP22 work items for recent new hires.

	Cessation/departure forms require facts not reliably inferable from Employee alone,
	so those remain event-driven through the Malaysia Employee Notification action.
	"""
	cutoff = add_days(today(), -30)
	for employee in frappe.get_all("Employee", filters={"status": "Active", "date_of_joining": [">=", cutoff]}, fields=["name", "company", "date_of_joining"], limit_page_length=5000):
		if frappe.db.exists("Malaysia Employee Notification", {"employee": employee.name, "form_type": "CP22", "trigger_date": employee.date_of_joining}):
			continue
		doc = frappe.new_doc("Malaysia Employee Notification")
		doc.employee = employee.name
		doc.company = employee.company
		doc.form_type = "CP22"
		doc.trigger_date = employee.date_of_joining
		doc.due_date = add_days(employee.date_of_joining, 30)
		doc.reason = "Automatically created from Employee Date of Joining"
		doc.insert(ignore_permissions=True)


def flag_expired_overrides():
	# The current design uses effective-dated lines without an approval workflow.
	# This scheduled control highlights profiles that have not been reviewed for a year.
	cutoff = add_days(today(), -365)
	for row in frappe.get_all("Statutory Coverage Profile", filters={"last_reviewed_on": ["<", cutoff]}, fields=["name", "employee"]):
		key = f"mw-statutory-review:{row.name}:{getdate(today()).year}"
		if frappe.cache.get_value(key):
			continue
		for user in frappe.get_users_with_role("Malaysia Payroll User"):
			frappe.get_doc({"doctype": "Notification Log", "subject": f"Review statutory settings for {row.employee}", "for_user": user, "type": "Alert", "document_type": "Statutory Coverage Profile", "document_name": row.name, "from_user": "Administrator"}).insert(ignore_permissions=True)
		frappe.cache.set_value(key, 1, expires_in_sec=30 * 24 * 3600)
