import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "malaysia_workforce"


def read(relative):
	return (PKG / relative).read_text()


def test_supported_runtime_and_framework_patch_set_are_pinned():
	pyproject = (ROOT / "pyproject.toml").read_text()
	package = json.loads((ROOT / "package.json").read_text())
	lock = json.loads((ROOT / "compatibility-lock.json").read_text())
	for expected in ('requires-python = ">=3.14,<3.15"', 'frappe = "==16.19.0"', 'erpnext = "==16.20.0"', 'hrms = "==16.7.1"'):
		assert expected in pyproject
	assert package["engines"]["node"] == ">=24"
	assert lock["runtime"]["python"] == "3.14"
	assert lock["runtime"]["database"] == "MariaDB 11.4"
	assert "image: mariadb:11.4" in (ROOT / ".github" / "workflows" / "ci.yml").read_text()


def test_staffing_is_a_native_layer_and_legacy_surfaces_are_absent():
	for relative in (
		"api/roster.py",
		"www/workforce.html",
		"public/js/workforce_portal.js",
		"malaysia_workforce/page/casual_roster_planner/casual_roster_planner.js",
		"malaysia_workforce/doctype/casual_roster/casual_roster.json",
		"malaysia_workforce/doctype/malaysia_payroll_run/malaysia_payroll_run.json",
	):
		assert not (PKG / relative).exists()
	hooks = read("hooks.py")
	assert '"Cafe Staffing Plan"' in hooks
	assert '"Casual Availability"' in hooks
	assert '"Shift Assignment"' in hooks
	assert '"Shift Type"' in hooks
	assert '"/workforce"' not in hooks
	assert "api.roster" not in hooks


def test_availability_uses_standard_web_form_and_workflow():
	web_form = json.loads(read("malaysia_workforce/web_form/casual_availability/casual_availability.json"))
	assert web_form["doc_type"] == "Casual Availability"
	assert web_form["login_required"] == 1
	assert web_form["apply_document_permissions"] == 1
	assert web_form["show_list"] == 1
	assert "employee" not in {field["fieldname"] for field in web_form["web_form_fields"]}
	assert [field["fieldname"] for field in web_form["list_columns"]] == [
		"status",
		"cycle_start",
		"submitted_on",
	]
	assert "def get_context(context):" in read(
		"malaysia_workforce/web_form/casual_availability/casual_availability.py"
	)
	client = read("malaysia_workforce/web_form/casual_availability/casual_availability.js")
	assert "Copy Previous Cycle" in client
	assert "frappe.confirm" in client
	master = read("setup/master_data.py")
	assert "Casual Availability Late Review" in master
	assert '"allow_self_approval": 0' in master


def test_allocator_publishes_only_standard_shift_assignments():
	services = read("staffing/services.py")
	shift_types = read("staffing/shift_types.py")
	assert 'frappe.new_doc("Shift Assignment")' in services
	assert "assignment.submit()" in services
	assert "custom_malaysia_staffing_recommendation_key" in services
	assert 'frappe.new_doc("Shift Type")' in shift_types
	assert "custom_malaysia_shift_fingerprint" in shift_types
	assert "prevent_managed_shift_deletion" in shift_types
	assert "Roster Selection" not in services


def test_standard_payroll_entry_is_the_only_payroll_control_document():
	services = read("payroll/services.py")
	events = read("payroll/events.py")
	jobs = read("payroll/jobs.py")
	fields = read("setup/custom_fields.py")
	for source in (services, events, jobs, fields):
		assert "Malaysia Payroll Run" not in source
		assert "custom_malaysia_payroll_run" not in source
	assert "def prepare_payroll_entry" in services
	assert 'doc.ref_doctype = "Payroll Entry"' in services
	assert "select_for_update" in services
	assert "custom_malaysia_work_record_reservation_status" in fields
	assert "custom_malaysia_statutory_preparation_status" in fields
	assert "maybe_finalize_payroll_entry_after_salary_slip_submit" in events
	assert "generate_statutory_files_for_payroll_entry" in jobs


def test_statutory_deductions_are_appended_in_the_component_helper():
	tree = ast.parse(read("payroll/salary_slip.py"))
	functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
	append_helper = functions["_append_deduction"]
	validator = functions["_validate_deductions_and_payment_deadline"]
	assert any(
		isinstance(node, ast.Call)
		and isinstance(node.func, ast.Attribute)
		and node.func.attr == "append"
		for node in ast.walk(append_helper)
	)
	assert "meta" not in {
		node.id for node in ast.walk(validator) if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
	}


def test_kiosk_creates_idempotent_standard_employee_checkins():
	attendance = read("api/attendance.py")
	assert '"doctype": "Employee Checkin"' in attendance
	assert "custom_kiosk_event_id" in attendance
	assert "hmac.compare_digest" in attendance
	assert "offline_queued" in attendance
	assert "DuplicateEntryError" in attendance
	assert "def clock(" not in attendance
	assert "You cannot approve your own attendance correction" in attendance


def test_migration_fails_before_removing_populated_legacy_schema():
	migration = read("setup/migrations.py")
	hooks = read("hooks.py")
	assert "def preflight_legacy_cleanup" in migration
	assert "SELECT COUNT(*)" in migration
	assert "Export and reconcile these records before upgrading" in migration
	assert "_remove_empty_legacy_schema" in migration
	assert 'before_migrate = "malaysia_workforce.install.before_migrate"' in hooks


def test_workspace_uses_standard_doctypes_report_and_hr_roster_route():
	workspace = json.loads(read("malaysia_workforce/workspace/malaysia_workforce/malaysia_workforce.json"))
	labels = {row["label"] for row in workspace["shortcuts"]}
	assert labels == {"Staffing Plans", "Coverage Gaps", "Payroll Entries"}
	assert "Casual Roster" not in workspace["content"]
	form = read("malaysia_workforce/doctype/cafe_staffing_plan/cafe_staffing_plan.js")
	assert 'frappe.set_route("hr", "roster")' in form
	report = json.loads(read("malaysia_workforce/report/cafe_coverage_gaps/cafe_coverage_gaps.json"))
	assert report["ref_doctype"] == "Cafe Staffing Plan"


def test_separated_roles_receive_narrow_standard_hrms_permissions():
	master = read("setup/master_data.py")
	assert '"Outlet Manager": {' in master
	assert '"Malaysia Payroll User": {' in master
	assert '"Malaysia HR Manager": {' in master
	assert '"Payroll Entry": {"read": 1, "write": 1, "create": 1' in master
	assert 'for name in ("Company", "Employee", "Payroll Entry", "Salary Slip", "Journal Entry")' in master
	assert "setup_custom_perms(doctype)" in master
	client = read("public/js/payroll_entry.js")
	assert 'frappe.perm.has_perm("Payroll Entry", 0, "submit", frm.doc)' in client
	assert 'const can_process = ["Malaysia Payroll User", "System Manager"]' in client
	assert 'const can_release = ["HR Manager", "Malaysia HR Manager", "System Manager"]' in client


def test_custom_doctype_json_contracts_are_consistent():
	root = PKG / "malaysia_workforce" / "doctype"
	custom_names = {json.loads(path.read_text())["name"] for path in root.glob("*/*.json")}
	for path in root.glob("*/*.json"):
		data = json.loads(path.read_text())
		fieldnames = [field["fieldname"] for field in data.get("fields", [])]
		assert len(fieldnames) == len(set(fieldnames)), f"Duplicate fieldname in {path}"
		assert len(data.get("field_order", [])) == len(set(data.get("field_order", []))), f"Duplicate field_order in {path}"
		assert set(fieldnames) == set(data.get("field_order", [])), f"field_order mismatch in {path}"
		for field in data.get("fields", []):
			if field.get("fieldtype") == "Table":
				assert field.get("options") in custom_names, f"Unknown child table in {path}"
			if field.get("fieldtype") in {"Link", "Dynamic Link", "Table"}:
				assert field.get("options"), f"Missing options in {path}:{field.get('fieldname')}"
			if field.get("fieldtype") == "Select" and field.get("default") not in (None, ""):
				options = {item.strip() for item in str(field.get("options") or "").splitlines()}
				assert str(field["default"]).strip() in options, f"Invalid select default in {path}"


def test_all_mutating_api_methods_explicitly_require_post():
	read_only = {"annual_incident_register"}
	for path in (PKG / "api").glob("*.py"):
		tree = ast.parse(path.read_text(), filename=str(path))
		for node in tree.body:
			if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
				continue
			decorator = next(
				(
					item
					for item in node.decorator_list
					if (isinstance(item, ast.Call) and isinstance(item.func, ast.Attribute) and item.func.attr == "whitelist")
					or (isinstance(item, ast.Attribute) and item.attr == "whitelist")
				),
				None,
			)
			if decorator is None or node.name in read_only:
				continue
			assert isinstance(decorator, ast.Call), f"{path.name}:{node.name} must require POST"
			methods = next((kw.value for kw in decorator.keywords if kw.arg == "methods"), None)
			assert methods and any(getattr(item, "value", None) == "POST" for item in methods.elts)


def test_release_manifest_is_git_archive_oriented():
	verification = (ROOT / "scripts" / "verify_release.py").read_text()
	generation = (ROOT / "scripts" / "generate_release_manifest.py").read_text()
	assert '["git", "write-tree"]' in verification
	assert '["git", "archive", tree' in verification
	assert '["git", "ls-files", "--cached", "-z"]' in generation
	assert (ROOT / ".gitattributes").read_text().strip()
