from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, getdate

from malaysia_workforce.utils import combine_date_time, end_after_start


class RosterStandby(Document):
	def validate(self):
		roster = frappe.get_doc("Casual Roster", self.roster)
		application = frappe.get_doc("Roster Application", self.application)
		if application.roster != self.roster:
			frappe.throw(_("The standby application must belong to this roster."))
		if application.employee != self.employee:
			frappe.throw(_("The standby employee must match the application employee."))
		if frappe.db.get_value("Employee", self.employee, "company") != roster.company:
			frappe.throw(_("The standby employee must belong to the roster company."))
		if not (getdate(roster.start_date) <= getdate(self.work_date) <= getdate(roster.end_date)):
			frappe.throw(_("Standby work date must be inside the roster period."))
		if int(self.standby_order or 0) <= 0:
			frappe.throw(_("Standby Order must be greater than zero."))
		if frappe.db.exists(
			"Roster Standby",
			{
				"roster": self.roster,
				"work_date": self.work_date,
				"standby_order": self.standby_order,
				"name": ["!=", self.name],
			},
		):
			frappe.throw(_("Standby Order {0} is already used for this roster and date.").format(self.standby_order))
		if frappe.db.exists(
			"Roster Standby",
			{
				"roster": self.roster,
				"work_date": self.work_date,
				"employee": self.employee,
				"name": ["!=", self.name],
			},
		):
			frappe.throw(_("This employee is already on the standby list for this date."))
		if bool(self.offered_from) != bool(self.offered_until):
			frappe.throw(_("Both Offered From and Offered Until are required together."))
		if self.offered_from and self.offered_until:
			start = combine_date_time(self.work_date, self.offered_from)
			end = end_after_start(start, combine_date_time(self.work_date, self.offered_until))
			if end <= start:
				frappe.throw(_("Standby offer end must be after its start."))
		if self.offer_status == "Offered" and not self.offer_expires_on:
			frappe.throw(_("Offer Expires On is required for an offered standby shift."))
		if self.offer_expires_on and get_datetime(self.offer_expires_on) <= get_datetime():
			if self.offer_status == "Offered":
				frappe.throw(_("A new standby offer must expire in the future."))
		if self.offer_status == "Accepted" and not self.selection:
			frappe.throw(_("An accepted standby offer must link to a Roster Selection."))
