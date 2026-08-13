import ast
import json
from pathlib import Path

import pytest

from malaysia_workforce.payroll.tax_validation import validate_tp1_rows


ROOT = Path(__file__).resolve().parents[2]


def _reject_duplicate_keys(pairs):
	result = {}
	for key, value in pairs:
		if key in result:
			raise ValueError(f"duplicate JSON key: {key}")
		result[key] = value
	return result


def test_all_json_files_reject_duplicate_keys():
	for path in ROOT.rglob("*.json"):
		if any(part in {".pytest_cache", "__pycache__", "node_modules", ".git"} for part in path.parts):
			continue
		json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)


def test_retired_parallel_hr_roles_are_not_shipped_as_current_permissions():
	legacy_roles = set(_legacy_role_replacements())
	for path in (ROOT / "malaysia_workforce").rglob("*.json"):
		if any(part in {".pytest_cache", "__pycache__"} for part in path.parts):
			continue
		payload = json.loads(path.read_text(encoding="utf-8"))
		assert not legacy_roles.intersection(_role_values(payload)), path


def test_workspace_fixture_path_matches_workspace_name():
	workspace_root = ROOT / "malaysia_workforce" / "malaysia_workforce" / "workspace"
	for path in workspace_root.glob("*/*.json"):
		payload = json.loads(path.read_text(encoding="utf-8"))
		expected = payload["name"].lower().replace(" ", "_").replace("-", "_")
		assert path.stem == expected
		assert path.parent.name == expected


def test_employee_tax_doctypes_use_native_hrms_self_service_role():
	root = ROOT / "malaysia_workforce" / "malaysia_workforce"
	for relative in (
		"doctype/malaysia_tax_declaration_tp1/malaysia_tax_declaration_tp1.json",
		"doctype/malaysia_previous_employment_tp3/malaysia_previous_employment_tp3.json",
	):
		payload = json.loads((root / relative).read_text(encoding="utf-8"))
		roles = set(_role_values(payload))
		assert "Employee Self Service" in roles
		assert "Employee" not in roles
	workspace = json.loads((root / "workspace/malaysia_payroll/malaysia_payroll.json").read_text(encoding="utf-8"))
	assert "Employee Self Service" not in set(_role_values(workspace))


def test_employee_self_service_compatibility_is_narrow_and_native():
	permissions = (ROOT / "malaysia_workforce" / "setup" / "permissions.py").read_text()
	hooks = (ROOT / "malaysia_workforce" / "hooks.py").read_text()

	assert set(_ess_document_types(permissions)) == {
		"Malaysia Tax Declaration TP1",
		"Malaysia Previous Employment TP3",
	}
	assert hooks.count("override_whitelisted_methods") == 1
	assert '"hrms.api._download_pdf": "malaysia_workforce.payroll.pdf.download_salary_slip_pdf"' in hooks
	assert "website_redirects" not in hooks
	assert not (ROOT / "malaysia_workforce" / "hrms_compat.py").exists()


def test_payslip_pdf_override_is_limited_to_the_native_hrms_endpoint():
	hooks = (ROOT / "malaysia_workforce" / "hooks.py").read_text()
	pdf = (ROOT / "malaysia_workforce" / "payroll" / "pdf.py").read_text()

	assert '"hrms.api._download_pdf": "malaysia_workforce.payroll.pdf.download_salary_slip_pdf"' in hooks
	assert "doctype != \"Salary Slip\"" in pdf
	assert '"wkhtmltopdf" if shutil.which("wkhtmltopdf") else "chrome"' in pdf


def test_salary_slip_has_one_native_employee_print_format():
	print_formats = (ROOT / "malaysia_workforce" / "setup" / "print_formats.py").read_text()
	install = (ROOT / "malaysia_workforce" / "install.py").read_text()

	assert 'SALARY_SLIP_PRINT_FORMAT = "Malaysia Payslip"' in print_formats
	assert '"doc_type": "Salary Slip"' in print_formats
	assert '"print_format_type": "Jinja"' in print_formats
	assert '"pdf_generator": None' in print_formats
	assert "ensure_salary_slip_print_format()" in install
	assert 'make_property_setter(' in print_formats
	assert '"default_print_format"' in print_formats

	html = print_formats.split('SALARY_SLIP_HTML = r"""', 1)[1].split('"""', 1)[0]
	for internal_field in (
		"custom_malaysia_rule_pack",
		"custom_malaysia_source_hash",
		"custom_malaysia_statutory_snapshot",
		"journal_entry",
		"custom_malaysia_validation_errors",
	):
		assert internal_field not in html

	assert "letter_head" in html
	assert "fallback-letterhead" in html
	assert "Net Pay" in html
	assert "Statutory Contributions" in html
	assert "page-break-inside: avoid" in html


def test_salary_slip_print_format_does_not_add_a_second_employee_format():
	print_formats = (ROOT / "malaysia_workforce" / "setup" / "print_formats.py").read_text()
	assert print_formats.count('SALARY_SLIP_PRINT_FORMAT = "Malaysia Payslip"') == 1
	assert "create_competing" not in print_formats


def test_tax_permission_refresh_is_one_time_and_narrow():
	patches = (ROOT / "malaysia_workforce" / "patches.txt").read_text()
	refresh = (
		ROOT
		/ "malaysia_workforce"
		/ "patches"
		/ "v1_0"
		/ "refresh_tax_declaration_permissions.py"
	).read_text()
	assert patches.count("refresh_tax_declaration_permissions") == 1
	assert "TAX_DECLARATION_DOCTYPES" in refresh
	assert '"Malaysia Tax Declaration TP1"' in refresh
	assert '"Malaysia Previous Employment TP3"' in refresh
	assert "for doctype in AUDITOR_SOURCE_DOCTYPES" not in refresh
	assert "reset_perms" not in refresh


def test_employee_tax_web_forms_send_drafts_through_native_workflow():
	root = ROOT / "malaysia_workforce" / "malaysia_workforce" / "web_form"
	for slug in ("my_tax_reliefs", "my_previous_employment"):
		payload = json.loads((root / slug / f"{slug}.json").read_text(encoding="utf-8"))
		script = (root / slug / f"{slug}.js").read_text(encoding="utf-8")
		assert payload["button_label"] == "Send for Review"
		assert payload["success_title"] == "Sent for Review"
		assert all(column.get("label") and column.get("fieldtype") for column in payload["list_columns"])
		assert any(column["fieldname"] == "workflow_state" for column in payload["list_columns"])
		assert "frappe.ready" in script
		assert "send_tax_declaration_for_review" in script
		fields = {row["fieldname"]: row for row in payload["web_form_fields"]}
		for fieldname in ("employee", "company"):
			assert fields[fieldname]["hidden"] == 1
			assert not fields[fieldname].get("reqd")

	for relative in (
		"doctype/malaysia_tax_declaration_tp1/malaysia_tax_declaration_tp1.py",
		"doctype/malaysia_previous_employment_tp3/malaysia_previous_employment_tp3.py",
	):
		source = (ROOT / "malaysia_workforce" / "malaysia_workforce" / relative).read_text()
		assert "frappe.flags.in_web_form" not in source


def test_tp3_supports_multiple_previous_employers_without_losing_annual_caps():
	tp3_source = (
		ROOT
		/ "malaysia_workforce"
		/ "malaysia_workforce"
		/ "doctype"
		/ "malaysia_previous_employment_tp3"
		/ "malaysia_previous_employment_tp3.py"
	).read_text()
	tax_source = (ROOT / "malaysia_workforce" / "payroll" / "tax_validation.py").read_text()
	assert "Approved TP3 {0} already exists" not in tp3_source
	assert "other_previous_rows" in tp3_source
	assert 'parents = frappe.get_all(doctype, filters=filters, pluck="name")' in tax_source


def test_localisation_does_not_reintroduce_parallel_hr_records():
	doctype_root = ROOT / "malaysia_workforce" / "malaysia_workforce" / "doctype"
	for slug in (
		"malaysia_employee_profile",
		"employee_work_agreement",
		"malaysia_payroll_run",
		"casual_availability",
		"cafe_staffing_plan",
		"shift_work_record",
	):
		assert not (doctype_root / slug / f"{slug}.json").exists(), slug

	custom_fields = (ROOT / "malaysia_workforce" / "setup" / "custom_fields.py").read_text()
	active_definition = custom_fields.split("fields = {", 1)[1].split("\n\tif only_doctypes:", 1)[0]
	assert '"Payroll Entry": [' not in active_definition


def test_routine_forms_hide_internal_filing_fingerprints():
	path = (
		ROOT
		/ "malaysia_workforce"
		/ "malaysia_workforce"
		/ "doctype"
		/ "malaysia_statutory_filing"
		/ "malaysia_statutory_filing.json"
	)
	payload = json.loads(path.read_text(encoding="utf-8"))
	fields = {row["fieldname"]: row for row in payload["fields"]}
	for fieldname in ("generated_file", "source_hash", "file_hash"):
		assert fields[fieldname].get("hidden") == 1


def test_custom_field_labels_are_native_inside_the_country_boundary():
	custom_fields = (ROOT / "malaysia_workforce" / "setup" / "custom_fields.py").read_text()
	active_definition = custom_fields.split("fields = {", 1)[1].split("\n\tif only_doctypes:", 1)[0]
	assert '"label": "Malaysia ' not in active_definition


def test_tp3_and_tp1_reliefs_share_one_annual_limit():
	rows = [
		{
			"relief_code": "C1",
			"amount": "5000",
			"claim_month": 2,
			"evidence_reference": "/private/files/first.pdf",
		},
		{
			"relief_code": "C1",
			"amount": "4000",
			"claim_month": 5,
			"evidence_reference": "/private/files/second.pdf",
		},
	]
	with pytest.raises(ValueError, match="annual limit"):
		validate_tp1_rows(rows, tax_year=2026)


def test_legacy_roles_never_auto_expand_access():
	replacements = _legacy_role_replacements()
	assert replacements
	assert all(not roles for roles in replacements.values())


def _legacy_role_replacements():
	path = ROOT / "malaysia_workforce" / "patches" / "v1_0" / "retire_parallel_hr_roles.py"
	for node in ast.parse(path.read_text(encoding="utf-8")).body:
		if isinstance(node, ast.Assign) and any(
			isinstance(target, ast.Name) and target.id == "LEGACY_ROLE_REPLACEMENTS"
			for target in node.targets
		):
			return ast.literal_eval(node.value)
	raise AssertionError("LEGACY_ROLE_REPLACEMENTS is missing")


def _ess_document_types(source):
	start = source.index("ESS_DOCUMENT_ACCESS = {")
	end = source.index("\n}\n", start)
	for line in source[start:end].splitlines()[1:]:
		if line.strip().startswith('"'):
			yield line.split('"', 2)[1]


def _role_values(value):
	if isinstance(value, dict):
		for key, item in value.items():
			if key in {"role", "allowed"} and isinstance(item, str):
				yield item
			yield from _role_values(item)
	elif isinstance(value, list):
		for item in value:
			yield from _role_values(item)
