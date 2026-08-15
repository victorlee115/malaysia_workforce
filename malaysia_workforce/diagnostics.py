from __future__ import annotations

import frappe
from frappe.utils import getdate, nowdate

from malaysia_workforce.payroll.events import employee_readiness
from malaysia_workforce.statutory.rule_pack import RULE_PACK, reviewed_through, rule_pack_hash


@frappe.whitelist()
def get_diagnostics(company: str) -> dict:
	frappe.get_doc("Company", company).check_permission("read")
	checks = []
	def add(name, ok, message): checks.append({"check": name, "ok": bool(ok), "message": message})
	enabled = frappe.db.get_value("Company", company, "custom_enable_malaysia_payroll")
	add("Company setup", enabled, "Statutory payroll is enabled." if enabled else "Enable Statutory Payroll on Company.")
	calendar_days = frappe.db.get_single_value("Payroll Settings", "include_holidays_in_total_working_days")
	add("Incomplete-month basis", calendar_days, "Calendar days are enabled." if calendar_days else "Enable holidays in total working days.")
	current = reviewed_through() >= getdate(nowdate())
	add("Statutory review", current, f"Rule pack {RULE_PACK} ({rule_pack_hash()[:12]}…) reviewed through {reviewed_through()}.")
	employee_rows = frappe.get_all(
		"Employee", filters={"company": company, "status": "Active"}, fields=["name", "user_id"]
	)
	employees = [row.name for row in employee_rows]
	blocked = {employee: employee_readiness(employee, company, nowdate()) for employee in employees}
	blocked = {employee: issues for employee, issues in blocked.items() if issues}
	add("Employee readiness", not blocked, f"{len(blocked)} of {len(employees)} active employees need attention.")
	pending = len(
		frappe.get_all(
			"Malaysia Statutory Filing",
			filters={"company": company, "docstatus": ["<", 2]},
			or_filters={"docstatus": 0, "reconciliation_status": ["!=", "Reconciled"]},
			pluck="name",
		)
	)
	add("Statutory filings", pending == 0, f"{pending} filings are not reconciled.")
	return {"company": company, "rule_pack": RULE_PACK, "checks": checks, "ready": all(row["ok"] for row in checks)}


@frappe.whitelist()
def assert_ready(company: str) -> dict:
	result = get_diagnostics(company)
	if not result["ready"]:
		failed = "; ".join(row["message"] for row in result["checks"] if not row["ok"])
		frappe.throw(f"Statutory payroll diagnostics failed: {failed}")
	return result
