from __future__ import annotations

import frappe


def execute():
	if not frappe.db.table_exists("Statutory Coverage Profile"):
		return
	for employee in frappe.get_all("Employee", filters={"status": "Active"}, pluck="name"):
		if frappe.db.exists("Statutory Coverage Profile", {"employee": employee, "effective_from": ["<=", frappe.utils.today()]}):
			continue
		doc = frappe.new_doc("Statutory Coverage Profile")
		doc.employee = employee
		doc.effective_from = frappe.utils.today()
		for scheme in ("EPF", "SOCSO", "EIS", "PCB", "LINDUNG 24 Jam"):
			doc.append("coverage_lines", {"scheme": scheme, "treatment": "Automatic", "effective_from": frappe.utils.today()})
		doc.insert(ignore_permissions=True)
