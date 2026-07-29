from __future__ import annotations

import frappe

APP_ACCESS_ROLES = {
	"System Manager",
	"HR Manager",
	"HR User",
	"Employee",
	"Casual Employee",
	"Roster Manager",
	"Malaysia HR Manager",
	"Malaysia Payroll User",
	"Statutory Administrator",
}

ROSTER_ADMIN_ROLES = {
	"System Manager",
	"HR Manager",
	"HR User",
	"Malaysia HR Manager",
}

ROSTER_MANAGER_ROLE = "Roster Manager"

TAX_PRIVILEGED_ROLES = {
	"System Manager",
	"HR Manager",
	"Malaysia HR Manager",
	"Malaysia Payroll User",
	"Statutory Administrator",
}

PAYROLL_PRIVILEGED_ROLES = {
	"System Manager",
	"HR Manager",
	"Malaysia HR Manager",
	"Malaysia Payroll User",
}


def _roles(user: str | None = None) -> set[str]:
	return set(frappe.get_roles(user or frappe.session.user))


def can_access_app() -> bool:
	return bool(_roles() & APP_ACCESS_ROLES)


def _current_employee_row(user: str | None = None):
	user = user or frappe.session.user
	if user == "Guest":
		return None
	return frappe.db.get_value(
		"Employee",
		{"user_id": user, "status": "Active"},
		["name", "company"],
		as_dict=True,
	)


def current_employee(user: str | None = None) -> str | None:
	row = _current_employee_row(user)
	return row.name if row else None


def current_employee_company(user: str | None = None) -> str | None:
	row = _current_employee_row(user)
	return row.company if row else None


def is_roster_admin(user: str | None = None) -> bool:
	return bool(_roles(user) & ROSTER_ADMIN_ROLES)


def is_roster_manager(user: str | None = None) -> bool:
	return ROSTER_MANAGER_ROLE in _roles(user)


def is_privileged(user: str | None = None) -> bool:
	"""Compatibility helper for roster code.

	A roster manager is privileged only for rosters explicitly assigned to that user;
	call :func:`can_manage_roster` before changing a concrete roster or linked record.
	"""
	return is_roster_admin(user) or is_roster_manager(user)


def is_tax_privileged(user: str | None = None) -> bool:
	return bool(_roles(user) & TAX_PRIVILEGED_ROLES)


def is_payroll_privileged(user: str | None = None) -> bool:
	return bool(_roles(user) & PAYROLL_PRIVILEGED_ROLES)


def _escape(value: str) -> str:
	return frappe.db.escape(value)


def _roster_manager_condition(table_name: str, roster_field: str, user: str) -> str:
	return (
		"EXISTS (SELECT 1 FROM `tabCasual Roster` mw_roster "
		f"WHERE mw_roster.name=`{table_name}`.`{roster_field}` "
		f"AND mw_roster.manager={_escape(user)})"
	)


def can_manage_roster(roster, user: str | None = None) -> bool:
	user = user or frappe.session.user
	if is_roster_admin(user):
		return True
	if not is_roster_manager(user):
		return False
	if isinstance(roster, str):
		manager = frappe.db.get_value("Casual Roster", roster, "manager")
	else:
		manager = getattr(roster, "manager", None)
	return bool(manager and manager == user)


def roster_query_condition(user: str | None = None) -> str:
	user = user or frappe.session.user
	if is_roster_admin(user):
		return ""
	if is_roster_manager(user):
		return f"`tabCasual Roster`.`manager`={_escape(user)}"
	row = _current_employee_row(user)
	if not row:
		return "1=0"
	return (
		f"`tabCasual Roster`.`company`={_escape(row.company)} AND ("
		"`tabCasual Roster`.`status`='Open for Applications' OR EXISTS "
		"(SELECT 1 FROM `tabRoster Application` mw_application "
		"WHERE mw_application.roster=`tabCasual Roster`.name "
		f"AND mw_application.employee={_escape(row.name)}))"
	)


def roster_application_query_condition(user: str | None = None) -> str:
	user = user or frappe.session.user
	if is_roster_admin(user):
		return ""
	if is_roster_manager(user):
		return _roster_manager_condition("tabRoster Application", "roster", user)
	employee = current_employee(user)
	return f"`tabRoster Application`.`employee`={_escape(employee)}" if employee else "1=0"


def roster_selection_query_condition(user: str | None = None) -> str:
	user = user or frappe.session.user
	if is_roster_admin(user):
		return ""
	if is_roster_manager(user):
		return _roster_manager_condition("tabRoster Selection", "roster", user)
	employee = current_employee(user)
	return f"`tabRoster Selection`.`employee`={_escape(employee)}" if employee else "1=0"


def shift_work_record_query_condition(user: str | None = None) -> str:
	user = user or frappe.session.user
	if is_payroll_privileged(user) or is_roster_admin(user):
		return ""
	if is_roster_manager(user):
		return _roster_manager_condition("tabShift Work Record", "roster", user)
	employee = current_employee(user)
	return f"`tabShift Work Record`.`employee`={_escape(employee)}" if employee else "1=0"


def roster_standby_query_condition(user: str | None = None) -> str:
	user = user or frappe.session.user
	if is_roster_admin(user):
		return ""
	if is_roster_manager(user):
		return _roster_manager_condition("tabRoster Standby", "roster", user)
	employee = current_employee(user)
	return f"`tabRoster Standby`.`employee`={_escape(employee)}" if employee else "1=0"


def employee_tax_query_condition(doctype: str, user: str | None = None) -> str:
	user = user or frappe.session.user
	if is_tax_privileged(user):
		return ""
	employee = current_employee(user)
	return f"`tab{doctype}`.`employee`={_escape(employee)}" if employee else "1=0"


def tp1_query_condition(user: str | None = None) -> str:
	return employee_tax_query_condition("Malaysia Tax Declaration TP1", user)


def tp3_query_condition(user: str | None = None) -> str:
	return employee_tax_query_condition("Malaysia Previous Employment TP3", user)


def annual_statement_query_condition(user: str | None = None) -> str:
	return employee_tax_query_condition("Malaysia Annual Remuneration Statement", user)


def _owns_employee_document(doc, user: str | None = None) -> bool:
	employee = current_employee(user)
	return bool(employee and getattr(doc, "employee", None) == employee)


def _linked_roster_name(doc) -> str | None:
	return getattr(doc, "roster", None)


def _can_manage_linked_roster(doc, user: str | None = None) -> bool:
	roster = _linked_roster_name(doc)
	return bool(roster and can_manage_roster(roster, user))


def roster_has_permission(doc, user=None, permission_type=None):
	user = user or frappe.session.user
	if is_roster_admin(user):
		return True
	if is_roster_manager(user):
		if permission_type == "create" and not getattr(doc, "name", None):
			return not getattr(doc, "manager", None) or getattr(doc, "manager", None) == user
		return can_manage_roster(doc, user)
	if permission_type not in {"read", "select"}:
		return False
	row = _current_employee_row(user)
	if not row or getattr(doc, "company", None) != row.company:
		return False
	if getattr(doc, "status", None) == "Open for Applications":
		return True
	return bool(
		frappe.db.exists(
			"Roster Application",
			{"roster": getattr(doc, "name", None), "employee": row.name},
		)
	)


def roster_application_has_permission(doc, user=None, permission_type=None):
	if is_roster_admin(user) or _can_manage_linked_roster(doc, user):
		return True
	if not _owns_employee_document(doc, user):
		return False
	if permission_type in {"read", "select", "create"}:
		return True
	if permission_type in {"write", "delete"}:
		return getattr(doc, "status", None) in {"Applied", "Withdrawn", None, ""}
	return False


def roster_selection_has_permission(doc, user=None, permission_type=None):
	if is_roster_admin(user) or _can_manage_linked_roster(doc, user):
		return True
	return _owns_employee_document(doc, user) and permission_type in {"read", "select", "print"}


def shift_work_record_has_permission(doc, user=None, permission_type=None):
	if is_payroll_privileged(user) or is_roster_admin(user) or _can_manage_linked_roster(doc, user):
		return True
	return _owns_employee_document(doc, user) and permission_type in {"read", "select", "print"}


def roster_standby_has_permission(doc, user=None, permission_type=None):
	if is_roster_admin(user) or _can_manage_linked_roster(doc, user):
		return True
	return _owns_employee_document(doc, user) and permission_type in {"read", "select", "print"}


def employee_owned_tax_has_permission(doc, user=None, permission_type=None):
	if is_tax_privileged(user):
		return True
	if not _owns_employee_document(doc, user):
		return False
	if permission_type in {"read", "select", "print", "create"}:
		return True
	if permission_type in {"write", "delete"}:
		return getattr(doc, "status", None) in {"Draft", None, ""}
	return False
