from __future__ import annotations

from collections.abc import Iterable


def skill_matches(required_skill: str | None, employee_skills: Iterable[str]) -> bool:
	"""Return whether the standard Frappe HR skill links satisfy a required Skill."""
	required = str(required_skill or "").strip()
	if not required:
		return True
	return required in {str(skill or "").strip() for skill in employee_skills if str(skill or "").strip()}


def employee_has_required_skill(employee: str, required_skill: str | None) -> bool:
	"""Check Frappe HR's Employee Skill Map instead of duplicating skills."""
	import frappe

	required = str(required_skill or "").strip()
	if not required:
		return True
	rows = frappe.db.sql(
		"""
		SELECT employee_skill.skill
		FROM `tabEmployee Skill` employee_skill
		INNER JOIN `tabEmployee Skill Map` skill_map ON skill_map.name = employee_skill.parent
		WHERE employee_skill.parenttype = 'Employee Skill Map'
		  AND skill_map.employee = %s
		  AND employee_skill.skill = %s
		LIMIT 1
		""",
		(employee, required),
		pluck=True,
	)
	return skill_matches(required, rows)
