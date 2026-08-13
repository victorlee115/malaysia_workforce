from __future__ import annotations

import frappe
from frappe.permissions import reset_perms


LOCALISATION_DOCTYPES = (
	"Malaysia CP38 Directive",
	"Malaysia Previous Employment TP3",
	"Malaysia Statutory Filing",
	"Malaysia Tax Declaration TP1",
)


def execute():
	"""Discard permissions written by the retired parallel HR application.

	This is deliberately a one-time patch.  The standard DocPerm rows shipped in
	the DocType JSON become authoritative, while administrator changes made after
	the lean migration remain intact on subsequent migrations.
	"""
	for doctype in LOCALISATION_DOCTYPES:
		if frappe.db.exists("DocType", doctype):
			reset_perms(doctype)

	frappe.clear_cache()
