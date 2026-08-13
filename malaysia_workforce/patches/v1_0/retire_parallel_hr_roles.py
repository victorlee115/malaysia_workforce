from __future__ import annotations

import frappe


LEGACY_ROLE_REPLACEMENTS = {
	"Casual Employee": (),
	"Outlet Manager": (),
	"Malaysia Payroll User": (),
	"Malaysia HR Manager": (),
	"Malaysia Kiosk": (),
	"Statutory Administrator": (),
	"Malaysia Workforce Auditor": (),
}


def users_with_legacy_roles() -> dict[str, list[str]]:
	result = {}
	for role in LEGACY_ROLE_REPLACEMENTS:
		users = sorted(set(frappe.get_all("Has Role", filters={"parenttype": "User", "role": role}, pluck="parent")))
		if users:
			result[role] = users
	return result


def require_reviewed_role_mapping() -> None:
	assigned = users_with_legacy_roles()
	if not assigned:
		return
	details = "; ".join(f"{role}: {', '.join(users)}" for role, users in assigned.items())
	frappe.throw(
		"Legacy roles cannot be translated safely because the standard roles grant different access. "
		"An administrator must assign the appropriate standard roles, verify Company User Permissions, "
		f"and remove each legacy role before migration. Assigned roles: {details}"
	)


def execute():
	"""Retire unassigned roles from the abandoned parallel HR application.

	There is deliberately no automatic role translation: names that sound
	equivalent do not prove equivalent permissions.
	"""
	require_reviewed_role_mapping()

	legacy_roles = tuple(LEGACY_ROLE_REPLACEMENTS)
	frappe.db.delete("Custom DocPerm", {"role": ["in", legacy_roles]})

	for role in legacy_roles:
		if frappe.db.exists("Role", role):
			frappe.delete_doc("Role", role, force=True, ignore_permissions=True)

	frappe.clear_cache()
