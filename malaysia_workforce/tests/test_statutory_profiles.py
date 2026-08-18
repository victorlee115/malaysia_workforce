import ast
import json
from pathlib import Path

from malaysia_workforce import hooks
from malaysia_workforce.payroll.profile import (
	SOCSO_EIS_LINDUNG_PROFILE,
	STANDARD_PAYROLL_PROFILE,
	STATUTORY_PROFILE_OPTIONS,
	applicable_schemes,
	is_socso_eis_lindung_profile,
	normalize_statutory_profile,
	scheme_applies,
)


ROOT = Path(__file__).resolve().parents[2]
STANDARD_SCHEMES = frozenset({"EPF", "SOCSO", "EIS", "HRD Corp", "PCB", "CP38", "Zakat"})
CONTRACTOR_SCHEMES = frozenset({"SOCSO", "EIS"})
EXCLUDED_FROM_CONTRACTOR = frozenset({"EPF", "HRD Corp", "PCB", "CP38", "Zakat"})


def test_statutory_profile_defaults_preserve_existing_employees():
	assert normalize_statutory_profile(None) == STANDARD_PAYROLL_PROFILE
	assert normalize_statutory_profile("") == STANDARD_PAYROLL_PROFILE
	assert is_socso_eis_lindung_profile(SOCSO_EIS_LINDUNG_PROFILE)
	assert not is_socso_eis_lindung_profile(STANDARD_PAYROLL_PROFILE)
	assert STATUTORY_PROFILE_OPTIONS.splitlines() == [STANDARD_PAYROLL_PROFILE, SOCSO_EIS_LINDUNG_PROFILE]


def test_blank_and_standard_include_every_scheme():
	for value in (None, "", STANDARD_PAYROLL_PROFILE):
		assert applicable_schemes(value) == STANDARD_SCHEMES
		for scheme in STANDARD_SCHEMES:
			assert scheme_applies(value, scheme)


def test_contractor_profile_is_only_socso_and_eis():
	assert applicable_schemes(SOCSO_EIS_LINDUNG_PROFILE) == CONTRACTOR_SCHEMES
	assert scheme_applies(SOCSO_EIS_LINDUNG_PROFILE, "SOCSO")
	assert scheme_applies(SOCSO_EIS_LINDUNG_PROFILE, "EIS")
	for scheme in EXCLUDED_FROM_CONTRACTOR:
		assert not scheme_applies(SOCSO_EIS_LINDUNG_PROFILE, scheme)


def test_unknown_profile_raises_from_applicable_schemes_but_scheme_applies_is_false():
	try:
		applicable_schemes("Not A Real Profile")
	except ValueError as exc:
		assert "Not A Real Profile" in str(exc)
	else:
		raise AssertionError("applicable_schemes must reject an unknown profile")
	assert not scheme_applies("Not A Real Profile", "EPF")
	assert not scheme_applies("Not A Real Profile", "SOCSO")


def test_employee_and_salary_slip_profile_fields_exist():
	tree = ast.parse((ROOT / "malaysia_workforce/setup/custom_fields.py").read_text(encoding="utf-8"))
	fieldnames = [
		value.value
		for node in ast.walk(tree)
		if isinstance(node, ast.Dict)
		for key, value in zip(node.keys, node.values)
		if isinstance(key, ast.Constant)
		and key.value == "fieldname"
		and isinstance(value, ast.Constant)
	]
	assert fieldnames.count("custom_malaysia_statutory_profile") == 2


def test_statutory_result_applicable_is_in_the_grid():
	payload = json.loads(
		(ROOT / "malaysia_workforce/malaysia_workforce/doctype/malaysia_statutory_result/malaysia_statutory_result.json").read_text(
			encoding="utf-8"
		)
	)
	applicable = next(field for field in payload["fields"] if field["fieldname"] == "applicable")
	assert applicable.get("in_list_view") == 1


def test_salary_slip_before_submit_hook_is_registered():
	assert hooks.doc_events["Salary Slip"]["before_submit"] == (
		"malaysia_workforce.payroll.salary_slip.validate_statutory_profile_snapshot"
	)
