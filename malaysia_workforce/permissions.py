from __future__ import annotations

import frappe

APP_ACCESS_ROLES = {
	"System Manager",
	"HR Manager",
	"HR User",
	"Employee",
	"Casual Employee",
	"Outlet Manager",
	"Malaysia HR Manager",
	"Malaysia Payroll User",
	"Statutory Administrator",
	"Malaysia Kiosk",
	"Malaysia Workforce Auditor",
}

STAFFING_MANAGER_ROLES = {"System Manager", "HR Manager", "HR User", "Malaysia HR Manager", "Outlet Manager"}
AUDITOR_ROLES = {"Malaysia Workforce Auditor"}
TAX_PRIVILEGED_ROLES = {"System Manager", "HR Manager", "Malaysia HR Manager", "Malaysia Payroll User", "Statutory Administrator", "Malaysia Workforce Auditor"}
PAYROLL_PRIVILEGED_ROLES = {"System Manager", "HR Manager", "Malaysia HR Manager", "Malaysia Payroll User"}


def _roles(user: str | None = None) -> set[str]:
	return set(frappe.get_roles(user or frappe.session.user))


def can_access_app() -> bool:
	return bool(_roles() & APP_ACCESS_ROLES)


def is_tax_privileged(user: str | None = None) -> bool:
	"""Return whether the current user may review employer-side tax records."""
	return bool(_roles(user) & TAX_PRIVILEGED_ROLES)


def _current_employee_row(user: str | None = None):
	user = user or frappe.session.user
	if user == "Guest":
		return None
	return frappe.db.get_value(
		"Employee", {"user_id": user, "status": "Active"}, ["name", "company"], as_dict=True
	)


def current_employee(user: str | None = None) -> str | None:
	row = _current_employee_row(user)
	return row.name if row else None


def _permitted_companies(doctype: str, user: str | None = None) -> set[str] | None:
	return _permitted_values("Company", doctype, user)


def _permitted_values(allow: str, doctype: str, user: str | None = None) -> set[str] | None:
	user = user or frappe.session.user
	rows = frappe.get_all(
		"User Permission",
		filters={"user": user, "allow": allow},
		fields=["for_value", "applicable_for"],
		limit=1000,
	)
	values = {
		row.for_value
		for row in rows
		if row.for_value and (not row.applicable_for or row.applicable_for == doctype)
	}
	return values or None


def _escape(value: str) -> str:
	return frappe.db.escape(value)


def _company_condition(doctype: str, user: str | None = None) -> str:
	companies = _permitted_companies(doctype, user)
	if _roles(user) & AUDITOR_ROLES and not companies:
		return "1=0"
	if not companies:
		return ""
	allowed = ", ".join(_escape(company) for company in sorted(companies))
	return f"`tab{doctype}`.`company` IN ({allowed})"


def company_scoped_query_condition(doctype: str, user: str | None = None) -> str:
	user = user or frappe.session.user
	if not (_roles(user) & TAX_PRIVILEGED_ROLES):
		return "1=0"
	return _company_condition(doctype, user)


def _staffing_query_condition(doctype: str, user: str | None = None) -> str:
	user = user or frappe.session.user
	roles = _roles(user)
	if not (roles & (STAFFING_MANAGER_ROLES | AUDITOR_ROLES)):
		return "1=0"
	conditions = [_company_condition(doctype, user)]
	branches = _permitted_values("Branch", doctype, user)
	if branches:
		allowed = ", ".join(_escape(branch) for branch in sorted(branches))
		conditions.append(f"COALESCE(`tab{doctype}`.`branch`, '') IN ('', {allowed})")
	if doctype == "Cafe Staffing Plan" and "Outlet Manager" in roles and not roles & {
		"System Manager",
		"HR Manager",
		"HR User",
		"Malaysia HR Manager",
	}:
		conditions.append(f"`tabCafe Staffing Plan`.`manager`={_escape(user)}")
	return " AND ".join(condition for condition in conditions if condition)


def coverage_template_query_condition(user: str | None = None) -> str:
	return _staffing_query_condition("Cafe Coverage Template", user)


def staffing_plan_query_condition(user: str | None = None) -> str:
	return _staffing_query_condition("Cafe Staffing Plan", user)


def employee_company_scoped_query_condition(doctype: str, user: str | None = None) -> str:
	user = user or frappe.session.user
	if not (_roles(user) & TAX_PRIVILEGED_ROLES):
		return "1=0"
	companies = _permitted_companies(doctype, user)
	if not companies:
		return "1=0" if _roles(user) & AUDITOR_ROLES else ""
	allowed = ", ".join(_escape(company) for company in sorted(companies))
	return (
		"EXISTS (SELECT 1 FROM `tabEmployee` mw_employee "
		f"WHERE mw_employee.name=`tab{doctype}`.`employee` AND mw_employee.company IN ({allowed}))"
	)


def company_scoped_has_permission(doc, user=None, permission_type=None, ptype=None):
	user = user or frappe.session.user
	permission_type = ptype or permission_type
	if not (_roles(user) & TAX_PRIVILEGED_ROLES):
		return False
	companies = _permitted_companies(doc.doctype, user)
	if _roles(user) & AUDITOR_ROLES:
		return permission_type in {"read", "select", "print", "report", "export"} and bool(
			companies and getattr(doc, "company", None) in companies
		)
	return not companies or getattr(doc, "company", None) in companies


def staffing_has_permission(doc, user=None, permission_type=None, ptype=None):
	user = user or frappe.session.user
	permission_type = ptype or permission_type
	roles = _roles(user)
	if not (roles & (STAFFING_MANAGER_ROLES | AUDITOR_ROLES)):
		return False
	companies = _permitted_companies(doc.doctype, user)
	if roles & AUDITOR_ROLES and (
		permission_type not in {"read", "select", "print", "report", "export"}
		or not companies
	):
		return False
	if companies and getattr(doc, "company", None) not in companies:
		return False
	branches = _permitted_values("Branch", doc.doctype, user)
	if branches and getattr(doc, "branch", None) and doc.branch not in branches:
		return False
	if doc.doctype == "Cafe Staffing Plan" and "Outlet Manager" in roles and not roles & {
		"System Manager", "HR Manager", "HR User", "Malaysia HR Manager"
	}:
		return doc.manager == user
	return True


def employee_company_scoped_has_permission(doc, user=None, permission_type=None, ptype=None):
	user = user or frappe.session.user
	permission_type = ptype or permission_type
	if not (_roles(user) & TAX_PRIVILEGED_ROLES):
		return False
	companies = _permitted_companies(doc.doctype, user)
	if _roles(user) & AUDITOR_ROLES and (
		permission_type not in {"read", "select", "print", "report", "export"}
		or not companies
	):
		return False
	if companies:
		company = frappe.db.get_value("Employee", getattr(doc, "employee", None), "company")
		return company in companies
	return True


def casual_availability_query_condition(user: str | None = None) -> str:
	user = user or frappe.session.user
	if _roles(user) & (STAFFING_MANAGER_ROLES | AUDITOR_ROLES):
		conditions = [_company_condition("Casual Availability", user)]
		branches = _permitted_values("Branch", "Casual Availability", user)
		if branches:
			allowed = ", ".join(_escape(branch) for branch in sorted(branches))
			conditions.append(
				"EXISTS (SELECT 1 FROM `tabEmployee` mw_employee "
				f"WHERE mw_employee.name=`tabCasual Availability`.`employee` AND mw_employee.branch IN ({allowed}))"
			)
		return " AND ".join(condition for condition in conditions if condition)
	employee = current_employee(user)
	return f"`tabCasual Availability`.`employee`={_escape(employee)}" if employee else "1=0"


def casual_availability_has_permission(doc, user=None, permission_type=None, ptype=None):
	user = user or frappe.session.user
	permission_type = ptype or permission_type
	roles = _roles(user)
	if roles & (STAFFING_MANAGER_ROLES | AUDITOR_ROLES):
		companies = _permitted_companies(doc.doctype, user)
		if roles & AUDITOR_ROLES and (
			permission_type not in {"read", "select", "print", "report", "export"}
			or not companies
		):
			return False
		if companies and getattr(doc, "company", None) not in companies:
			return False
		branches = _permitted_values("Branch", doc.doctype, user)
		if branches:
			branch = frappe.db.get_value("Employee", doc.employee, "branch")
			return branch in branches
		return True
	return bool(current_employee(user) and doc.employee == current_employee(user))


def shift_work_record_query_condition(user: str | None = None) -> str:
	user = user or frappe.session.user
	if _roles(user) & (PAYROLL_PRIVILEGED_ROLES | STAFFING_MANAGER_ROLES | AUDITOR_ROLES):
		return _company_condition("Shift Work Record", user)
	employee = current_employee(user)
	return f"`tabShift Work Record`.`employee`={_escape(employee)}" if employee else "1=0"


def shift_work_record_has_permission(doc, user=None, permission_type=None, ptype=None):
	user = user or frappe.session.user
	permission_type = ptype or permission_type
	roles = _roles(user)
	if roles & (PAYROLL_PRIVILEGED_ROLES | STAFFING_MANAGER_ROLES | AUDITOR_ROLES):
		companies = _permitted_companies(doc.doctype, user)
		if roles & AUDITOR_ROLES:
			return permission_type in {"read", "select", "print", "report", "export"} and bool(
				companies and getattr(doc, "company", None) in companies
			)
		return not companies or getattr(doc, "company", None) in companies
	return permission_type in {"read", "select", "print"} and doc.employee == current_employee(user)


def employee_tax_query_condition(doctype: str, user: str | None = None) -> str:
	user = user or frappe.session.user
	if _roles(user) & TAX_PRIVILEGED_ROLES:
		return company_scoped_query_condition(doctype, user)
	employee = current_employee(user)
	return f"`tab{doctype}`.`employee`={_escape(employee)}" if employee else "1=0"


def tp1_query_condition(user: str | None = None) -> str:
	return employee_tax_query_condition("Malaysia Tax Declaration TP1", user)


def tp3_query_condition(user: str | None = None) -> str:
	return employee_tax_query_condition("Malaysia Previous Employment TP3", user)


def annual_statement_query_condition(user: str | None = None) -> str:
	return employee_tax_query_condition("Malaysia Annual Remuneration Statement", user)


def employee_profile_query_condition(user: str | None = None) -> str:
	return company_scoped_query_condition("Malaysia Employee Profile", user)


def work_agreement_query_condition(user: str | None = None) -> str:
	return company_scoped_query_condition("Employee Work Agreement", user)


def coverage_profile_query_condition(user: str | None = None) -> str:
	return company_scoped_query_condition("Statutory Coverage Profile", user)


def accumulator_query_condition(user: str | None = None) -> str:
	return company_scoped_query_condition("Monthly Statutory Accumulator", user)


def submission_query_condition(user: str | None = None) -> str:
	return company_scoped_query_condition("Statutory Submission", user)


def employee_notification_query_condition(user: str | None = None) -> str:
	return company_scoped_query_condition("Malaysia Employee Notification", user)


def treatment_history_query_condition(user: str | None = None) -> str:
	return employee_company_scoped_query_condition("Statutory Treatment History", user)


def employee_owned_tax_has_permission(doc, user=None, permission_type=None, ptype=None):
	user = user or frappe.session.user
	permission_type = ptype or permission_type
	if _roles(user) & TAX_PRIVILEGED_ROLES:
		return company_scoped_has_permission(doc, user, permission_type)
	return doc.employee == current_employee(user)
