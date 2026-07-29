import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "malaysia_workforce"


def test_supported_runtime_and_frappe_major_are_pinned():
	pyproject = (ROOT / "pyproject.toml").read_text()
	package = json.loads((ROOT / "package.json").read_text())
	assert 'requires-python = ">=3.14,<3.15"' in pyproject
	assert 'frappe = ">=16.0.0,<17.0.0"' in pyproject
	assert package["engines"]["node"] == ">=24"


def test_critical_payroll_lifecycle_hooks_are_registered():
	hooks = (PKG / "hooks.py").read_text()
	assert '"Salary Slip": {' in hooks
	assert '"on_submit": "malaysia_workforce.payroll.salary_slip.freeze_statutory_snapshot"' in hooks
	assert '"Payroll Entry": {' in hooks
	assert '"before_cancel": "malaysia_workforce.payroll.events.before_payroll_entry_cancel"' in hooks
	salary_slip = (PKG / "payroll" / "salary_slip.py").read_text()
	assert "maybe_finalize_run_after_salary_slip_submit(doc)" in salary_slip
	events = (PKG / "payroll" / "events.py").read_text()
	assert "submitted != expected or draft" in events
	assert "FOR UPDATE" in events


def test_payroll_generation_is_idempotent_and_never_overwrites_salary_structure_amount():
	services = (PKG / "payroll" / "services.py").read_text()
	assert "FOR UPDATE" in services
	assert "doc.overwrite_salary_structure_amount = 0" in services
	assert 'source_work_record_hash' in services


def test_permission_contract_contains_company_and_manager_scoping():
	permissions = (PKG / "permissions.py").read_text()
	assert "`tabCasual Roster`.`company`" in permissions
	assert "`tabCasual Roster`.`manager`" in permissions
	assert "mw_roster.manager" in permissions
	jobs = (PKG / "roster" / "jobs.py").read_text()
	assert "roster.company != employee.company" in jobs


def test_all_mutating_whitelisted_api_functions_are_post_only():
	get_only = {
		"get_employee_dashboard",
		"get_roster_details",
		"manager_roster",
		"recommend",
	}
	for path in (PKG / "api").glob("*.py"):
		tree = ast.parse(path.read_text(), filename=str(path))
		for node in tree.body:
			if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
				continue
			whitelist = None
			for decorator in node.decorator_list:
				if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute) and decorator.func.attr == "whitelist":
					whitelist = decorator
				elif isinstance(decorator, ast.Attribute) and decorator.attr == "whitelist":
					whitelist = decorator
			if whitelist is None or node.name in get_only:
				continue
			assert isinstance(whitelist, ast.Call), f"{path.name}:{node.name} must explicitly require POST"
			methods = next((kw.value for kw in whitelist.keywords if kw.arg == "methods"), None)
			assert methods is not None, f"{path.name}:{node.name} must explicitly require POST"
			assert any(isinstance(item, ast.Constant) and item.value == "POST" for item in methods.elts)


def test_custom_doctype_json_contracts_are_consistent():
	doctype_root = PKG / "malaysia_workforce" / "doctype"
	custom_names = {json.loads(path.read_text())["name"] for path in doctype_root.glob("*/*.json")}
	for path in doctype_root.glob("*/*.json"):
		data = json.loads(path.read_text())
		fields = data.get("fields", [])
		fieldnames = [field["fieldname"] for field in fields]
		assert len(fieldnames) == len(set(fieldnames)), f"Duplicate fieldname in {path}"
		assert len(data.get("field_order", [])) == len(set(data.get("field_order", []))), f"Duplicate field_order in {path}"
		assert set(fieldnames) == set(data.get("field_order", [])), f"field_order mismatch in {path}"
		for field in fields:
			if field.get("fieldtype") == "Table":
				assert field.get("options") in custom_names, f"Unknown child table {field.get('options')} in {path}"
			if field.get("fieldtype") in {"Link", "Dynamic Link", "Table"}:
				assert field.get("options"), f"Missing options for {field.get('fieldname')} in {path}"
			if field.get("fieldtype") == "Select" and field.get("default") not in (None, ""):
				options = {item.strip() for item in str(field.get("options") or "").splitlines()}
				assert str(field["default"]).strip() in options, f"Invalid select default in {path}:{field['fieldname']}"


def test_managed_master_data_fails_safe_and_preserves_user_classification_on_migrate():
	master_data = (PKG / "setup" / "master_data.py").read_text()
	assert "Reserved Salary Component Conflict" in master_data
	assert "doc.type != expected_type" in master_data
	assert 'not int(doc.get("custom_malaysia_component") or 0)' in master_data
	assert "Reserved Print Format Conflict" in master_data
	assert "Never overwrite payroll formulas" in master_data
	assert "doc.custom_malaysia_component = 1" in master_data


def test_casual_assignment_uses_actual_employee_payroll_start_and_validates_reserved_structure():
	services = (PKG / "payroll" / "services.py").read_text()
	assert "def _assignment_effective_date" in services
	assert 'frappe.db.get_value("Employee", employee, "date_of_joining")' in services
	assert "assignment.from_date = effective_date" in services
	assert "Casual Salary Structure Conflict" in services
	assert "component not in {row.salary_component for row in structure.earnings}" in services


def test_legacy_epf_csv_is_fail_closed_and_never_portal_ready():
	service = (PKG / "statutory" / "submission_service.py").read_text()
	settings = (PKG / "malaysia_workforce" / "doctype" / "malaysia_workforce_settings" / "malaysia_workforce_settings.json").read_text()
	doc = (PKG / "malaysia_workforce" / "doctype" / "statutory_submission" / "statutory_submission.py").read_text()
	assert "KWSP-ECARUMAN-LEGACY-CSV-UNVERIFIED" in service
	assert "_ensure_legacy_epf_uat_enabled" in service
	assert "enable_legacy_epf_ecaruman_csv_for_uat" in settings
	assert "must never be" in service and "portal-ready" in service
	assert "A legacy e-Caruman UAT file cannot be marked" in doc


def test_required_skills_use_standard_frappe_hr_skill_map():
	selection = (PKG / "malaysia_workforce" / "doctype" / "roster_selection" / "roster_selection.py").read_text()
	services = (PKG / "roster" / "services.py").read_text()
	skills = (PKG / "roster" / "skills.py").read_text()
	assert "Employee Skill Map" in skills
	assert "Employee Skill" in skills
	assert "employee_has_required_skill" in selection
	assert "employee_has_required_skill" in services
	coverage = (PKG / "malaysia_workforce" / "doctype" / "roster_coverage_requirement" / "roster_coverage_requirement.json").read_text()
	assert '"fieldname": "required_skill"' in coverage
	assert '"options": "Skill"' in coverage


def test_portal_error_messages_are_html_escaped():
	portal = (PKG / "public" / "js" / "workforce_portal.js").read_text()
	assert 'message: escape(error.message || String(error))' in portal
	assert 'message: error.message || String(error)' not in portal


def test_release_documents_and_installer_match_rc4():
	for relative in (
		"README.md",
		"docs/INSTALLATION.md",
		"docs/VALIDATION.md",
		"docs/RELEASE_VALIDATION.md",
		"malaysia_workforce/install.py",
	):
		text = (ROOT / relative).read_text()
		assert "1.0.0-rc.1" not in text
	assert "1.0.0-rc.4" in (ROOT / "README.md").read_text()
	assert "56 passed" in (ROOT / "docs/VALIDATION.md").read_text()


def test_live_bench_harness_uses_real_entrypoints_and_no_phantom_setup_api():
	script = (ROOT / "scripts" / "run_live_bench_test.sh").read_text()
	live_test = (PKG / "live_tests" / "test_installation.py").read_text()
	hooks = (PKG / "hooks.py").read_text()
	assert "malaysia_workforce.api.setup.bootstrap_company" not in script
	assert "bench --site \"$SITE\" migrate" in script
	assert "bench --site \"$SITE\" run-tests --module malaysia_workforce.live_tests.test_installation" in script
	assert "http://127.0.0.1:8000/api/method/ping" in script
	assert "./env/bin/python" in script
	assert 'bench --site "$SITE" set-config allow_tests true' in script
	assert "malaysia_workforce.diagnostics.assert_ready" in script
	assert "from malaysia_workforce import hooks as mw_hooks" in live_test
	for target in (
		"malaysia_workforce.attendance.events.on_employee_checkin",
		"malaysia_workforce.attendance.events.on_shift_assignment_submit",
		"malaysia_workforce.payroll.salary_slip.apply_malaysia_statutory_calculations",
		"malaysia_workforce.payroll.events.validate_payroll_readiness",
		"malaysia_workforce.compliance.jobs.refresh_obligations",
		"malaysia_workforce.statutory.submission_service.generate_submission_file",
	):
		assert target in hooks or target in live_test


def test_employee_portal_supports_frappe_v16_bootstrap4_modal_api():
	portal = (PKG / "public" / "js" / "workforce_portal.js").read_text()
	template = (PKG / "www" / "workforce.html").read_text()
	assert "window.jQuery(element).modal(action)" in portal
	assert 'modal("show")' in portal
	assert 'modal("hide")' in portal
	assert "bootstrap.Modal.getOrCreateInstance(document.getElementById" not in portal
	assert 'data-dismiss="modal"' in template
	assert 'class="btn-close"' not in template


def test_split_shifts_follow_standard_frappe_hr_multiple_assignment_setting():
	application = (PKG / "malaysia_workforce" / "doctype" / "roster_application" / "roster_application.py").read_text()
	selection = (PKG / "malaysia_workforce" / "doctype" / "roster_selection" / "roster_selection.py").read_text()
	api = (PKG / "api" / "roster.py").read_text()
	portal = (PKG / "public" / "js" / "workforce_portal.js").read_text()
	for source in (application, selection, api):
		assert "allow_multiple_shift_assignments" in source
	assert "same_date_shift_assignments" in selection
	assert '"allow_split_shifts"' in api
	assert "selectedRoster.allow_split_shifts" in portal
