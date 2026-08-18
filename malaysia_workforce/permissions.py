from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from malaysia_workforce.payroll.validation import (
	employee_uses_socso_eis_lindung_profile,
	ensure_employee_tax_profile,
)

TAX_PRIVILEGED = {"System Manager", "HR Manager"}
FILING_PRIVILEGED = {"System Manager", "HR Manager", "Accounts Manager"}
READ_ONLY = {"Auditor"}
EMPLOYEE_TAX_DECLARATIONS = {
	"Malaysia Tax Declaration TP1",
	"Malaysia Previous Employment TP3",
}


def _roles(user: str | None = None) -> set[str]:
	return set(frappe.get_roles(user or frappe.session.user))


def current_employee(user: str | None = None) -> str | None:
	user = user or frappe.session.user
	if user == "Guest":
		return None
	return frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")


def is_tax_privileged(user: str | None = None) -> bool:
	return bool(_roles(user) & (TAX_PRIVILEGED | READ_ONLY))


@frappe.whitelist()
def employee_tax_defaults() -> dict:
	"""Return the signed-in employee context for native TP1 and TP3 forms."""
	employee = current_employee()
	if not employee:
		frappe.throw(_("Your User is not linked to an active Employee."), frappe.PermissionError)
	ensure_employee_tax_profile(employee)
	return {
		"employee": employee,
		"company": frappe.db.get_value("Employee", employee, "company"),
		"tax_year": getdate().year,
		"declaration_date": nowdate(),
	}


@frappe.whitelist(methods=["POST"])
def send_tax_declaration_for_review(doctype: str, name: str) -> dict:
	"""Apply the native employee workflow after a Web Form has saved its Draft."""
	if doctype not in EMPLOYEE_TAX_DECLARATIONS:
		frappe.throw(_("Unsupported tax declaration type."), frappe.PermissionError)
	employee = current_employee()
	if not employee:
		frappe.throw(_("Your User is not linked to an active Employee."), frappe.PermissionError)
	ensure_employee_tax_profile(employee)
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("write")
	if doc.employee != employee:
		frappe.throw(_("You can only send your own declaration for review."), frappe.PermissionError)
	if doc.docstatus != 0:
		frappe.throw(_("Only a Draft declaration can be sent for review."))
	state = doc.get("workflow_state") or "Draft"
	if state == "Pending Review":
		return {"name": doc.name, "workflow_state": state}
	if state != "Draft":
		frappe.throw(_("This declaration cannot be sent from workflow state {0}.").format(state))

	from frappe.model.workflow import apply_workflow

	doc = apply_workflow(doc, "Send for Review")
	return {"name": doc.name, "workflow_state": doc.workflow_state}


def _privileged_for(doctype: str) -> set[str]:
	return FILING_PRIVILEGED if doctype == "Malaysia Statutory Filing" else TAX_PRIVILEGED


def _allowed_companies(user: str, doctype: str) -> set[str] | None:
	rows = frappe.get_all(
		"User Permission",
		filters={"user": user, "allow": "Company"},
		fields=["for_value", "applicable_for"],
	)
	values = {row.for_value for row in rows if not row.applicable_for or row.applicable_for == doctype}
	return values or None


def employee_tax_query(doctype: str, user: str | None = None) -> str:
	user = user or frappe.session.user
	if _roles(user) & (TAX_PRIVILEGED | READ_ONLY):
		return company_query(user, doctype)
	employee = current_employee(user)
	if employee and employee_uses_socso_eis_lindung_profile(employee):
		return "1=0"
	return f"`tab{doctype}`.`employee`={frappe.db.escape(employee)}" if employee else "1=0"


def company_query(user: str | None = None, doctype: str = "Malaysia Statutory Filing") -> str:
	user = user or frappe.session.user
	if not _roles(user) & (_privileged_for(doctype) | READ_ONLY):
		return "1=0"
	companies = _allowed_companies(user, doctype)
	if not companies:
		return "1=0" if _roles(user) & READ_ONLY else ""
	values = ", ".join(frappe.db.escape(value) for value in sorted(companies))
	return f"`tab{doctype}`.`company` IN ({values})"


def tp1_query(user: str | None = None) -> str:
	return employee_tax_query("Malaysia Tax Declaration TP1", user)


def tp3_query(user: str | None = None) -> str:
	return employee_tax_query("Malaysia Previous Employment TP3", user)


def cp38_query(user: str | None = None) -> str:
	return company_query(user, "Malaysia CP38 Directive")


def filing_query(user: str | None = None) -> str:
	return company_query(user, "Malaysia Statutory Filing")


def employee_tax_permission(doc, user=None, permission_type=None, ptype=None):
	if doc is None:
		return None
	user = user or frappe.session.user
	permission_type = ptype or permission_type
	roles = _roles(user)
	if roles & READ_ONLY:
		return permission_type in {"read", "select", "report", "print", "export"} and company_permission(
			doc, user, permission_type
		)
	if roles & TAX_PRIVILEGED:
		return company_permission(doc, user, permission_type)
	if employee_uses_socso_eis_lindung_profile(getattr(doc, "employee", None)):
		return False
	return getattr(doc, "employee", None) == current_employee(user)


def company_permission(doc, user=None, permission_type=None, ptype=None):
	if doc is None:
		return None
	user = user or frappe.session.user
	permission_type = ptype or permission_type
	roles = _roles(user)
	if not roles & (_privileged_for(doc.doctype) | READ_ONLY):
		return False
	if roles & READ_ONLY and permission_type not in {"read", "select", "report", "print", "export"}:
		return False
	companies = _allowed_companies(user, doc.doctype)
	if roles & READ_ONLY and not companies:
		return False
	return not companies or getattr(doc, "company", None) in companies
