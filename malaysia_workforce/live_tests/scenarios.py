from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, time, timedelta

import frappe
from frappe.model.workflow import apply_workflow
from frappe.utils import add_days, getdate
from frappe.utils.password import update_password

from malaysia_workforce.api.attendance import kiosk_clock, set_kiosk_credential


COMPANY = "MW E2E Cafe Sdn Bhd"
EMPLOYEE_EMAIL = "mw.employee@example.com"
HR_MANAGER_EMAIL = "mw.manager@example.com"
PAYROLL_EMAIL = "mw.payroll@example.com"
RELEASER_EMAIL = "mw.releaser@example.com"
AUDITOR_EMAIL = "mw.auditor@example.com"
KIOSK_ID = "MW-CAFE-KIOSK-01"
KIOSK_SECRET = "mw-e2e-kiosk-signing-secret"
KIOSK_CREDENTIAL = "2468"


def permission_probe(user: str, doctype: str, name: str) -> dict:
	"""Return live permission evidence without changing the target document."""
	frappe.set_user(user)
	doc = frappe.get_doc(doctype, name)
	result = {
		"roles": frappe.get_roles(user),
		"doctype_read": bool(frappe.has_permission(doctype, "read", user=user)),
		"document_read": bool(frappe.has_permission(doctype, "read", doc=doc, user=user)),
	}
	frappe.set_user("Administrator")
	return result


def _ensure_user(email: str, first_name: str, roles: tuple[str, ...], password: str) -> str:
	for role in roles:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(ignore_permissions=True)
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": first_name,
				"enabled": 1,
				"send_welcome_email": 0,
				"roles": [{"role": role} for role in roles],
			}
		).insert(ignore_permissions=True)
		update_password(email, password)
	else:
		doc = frappe.get_doc("User", email)
		existing = {row.role for row in doc.roles}
		for role in roles:
			if role not in existing:
				doc.append("roles", {"role": role})
		if {row.role for row in doc.roles} != existing:
			doc.save(ignore_permissions=True)
	return email


def _ensure_company_permission(user: str, company: str) -> None:
	if frappe.db.exists("User Permission", {"user": user, "allow": "Company", "for_value": company}):
		return
	frappe.get_doc(
		{
			"doctype": "User Permission",
			"user": user,
			"allow": "Company",
			"for_value": company,
			"apply_to_all_doctypes": 1,
		}
	).insert(ignore_permissions=True)


def _mark_setup_complete() -> None:
	for app in ("frappe", "erpnext"):
		for name in frappe.get_all("Installed Application", filters={"app_name": app}, pluck="name"):
			frappe.db.set_value("Installed Application", name, "is_setup_complete", 1, update_modified=False)
	frappe.db.set_single_value("System Settings", "setup_complete", 1)
	frappe.db.set_single_value("System Settings", "time_zone", "Asia/Kuala_Lumpur")
	frappe.db.set_single_value("Global Defaults", "country", "Malaysia")
	frappe.db.set_single_value("Global Defaults", "default_currency", "MYR")
	frappe.defaults.set_global_default("country", "Malaysia")
	frappe.defaults.set_global_default("currency", "MYR")
	frappe.defaults.set_global_default("time_zone", "Asia/Kuala_Lumpur")
	frappe.db.set_single_value("Malaysia Workforce Settings", "enabled", 1)
	frappe.clear_cache()


def prepare_browser_site() -> None:
	_mark_setup_complete()
	if frappe.db.exists("Company", COMPANY):
		company = COMPANY
	else:
		company = seed_demo()["company"]
	_ensure_browser_availability_collection(company)
	frappe.db.commit()


def _ensure_browser_availability_collection(company: str) -> str:
	"""Keep the next cycle open so the browser can exercise copy-and-submit UX."""
	previous_cycle = frappe.db.get_value(
		"Casual Availability",
		{"company": company, "status": "Submitted"},
		"cycle_start",
		order_by="cycle_start desc",
	)
	cycle_start = add_days(previous_cycle or getdate(), 14)
	plan_name = frappe.db.get_value(
		"Cafe Staffing Plan",
		{
			"company": company,
			"cycle_start": cycle_start,
			"workflow_state": "Collecting Availability",
		},
		"name",
	)
	if plan_name:
		return plan_name
	if frappe.db.exists(
		"Cafe Staffing Plan",
		{"company": company, "cycle_start": cycle_start, "workflow_state": ["!=", "Superseded"]},
	):
		return frappe.db.get_value(
			"Cafe Staffing Plan",
			{"company": company, "cycle_start": cycle_start, "workflow_state": ["!=", "Superseded"]},
			"name",
		)

	template_name = "MW E2E Future Availability Coverage"
	if not frappe.db.exists("Cafe Coverage Template", template_name):
		template_name = frappe.get_doc(
			{
				"doctype": "Cafe Coverage Template",
				"template_name": template_name,
				"company": company,
				"effective_from": cycle_start,
				"effective_until": add_days(cycle_start, 13),
				"coverage_rows": [
					{
						"weekday": cycle_start.strftime("%A"),
						"start_time": time(8),
						"end_time": time(12),
						"required_headcount": 1,
						"designation": "Barista",
						"criticality": "Critical",
					}
				],
			}
		).insert(ignore_permissions=True).name

	plan = frappe.get_doc(
		{
			"doctype": "Cafe Staffing Plan",
			"plan_title": "MW E2E Next-cycle Availability Collection",
			"company": company,
			"manager": HR_MANAGER_EMAIL,
			"cycle_start": cycle_start,
			"coverage_template": template_name,
		}
	).insert(ignore_permissions=True)
	return apply_workflow(plan.as_dict(), "Open Availability").name


def _ensure_company() -> str:
	_mark_setup_complete()
	# ERPNext's Company hook creates a Goods in Transit warehouse and expects the
	# standard Warehouse Type master to exist even on a minimal test site.
	if not frappe.db.exists("Warehouse Type", "Transit"):
		frappe.get_doc({"doctype": "Warehouse Type", "name": "Transit"}).insert(ignore_permissions=True)
	if not frappe.db.exists("Issue Priority", "High"):
		frappe.get_doc({"doctype": "Issue Priority", "name": "High"}).insert(ignore_permissions=True)
	if not frappe.db.exists("Company", COMPANY):
		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": COMPANY,
				"abbr": "MWC",
				"country": "Malaysia",
				"default_currency": "MYR",
				"chart_of_accounts": "Standard",
			}
		).insert(ignore_permissions=True)
	frappe.db.set_value(
		"Company",
		COMPANY,
		{
			"custom_enable_malaysia_payroll": 1,
			"custom_malaysia_jurisdiction": "Peninsular Malaysia",
			"custom_malaysia_citizenship_policy": "Malaysian Citizens Only",
			"custom_malaysia_rule_review_deadline": "2026-12-31",
			"custom_hrd_corp_registered": 1,
			"custom_hrd_corp_registration_number": "HRD-MW-E2E",
			"custom_hrd_levy_rate": 1,
			"custom_malaysia_bank_file_format": "Generic CSV (UAT Only)",
		},
		update_modified=False,
	)
	return COMPANY


def _ensure_designation_and_shift() -> tuple[str, str]:
	designation = "Barista"
	if not frappe.db.exists("Designation", designation):
		frappe.get_doc({"doctype": "Designation", "designation_name": designation}).insert(ignore_permissions=True)
	shift = "MW E2E Casual Base"
	if not frappe.db.exists("Shift Type", shift):
		doc = frappe.new_doc("Shift Type")
		doc.name = shift
		doc.shift_type = shift
		doc.start_time = time(8)
		doc.end_time = time(16)
		doc.enable_auto_attendance = 1
		doc.insert(ignore_permissions=True)
	settings = frappe.get_doc("Malaysia Workforce Settings")
	settings.flexible_shift_template = shift
	settings.staffing_slot_minutes = 30
	settings.preferred_minimum_shift_hours = 4
	settings.normal_minimum_shift_hours = 2
	settings.maximum_recommended_shift_hours = 8
	settings.save(ignore_permissions=True)
	return designation, shift


def _ensure_employee(company: str, designation: str) -> str:
	employee = frappe.db.get_value("Employee", {"employee_number": "MW-E2E-001"}, "name")
	if not employee:
		if not frappe.db.exists("Gender", "Female"):
			frappe.get_doc({"doctype": "Gender", "gender": "Female"}).insert(ignore_permissions=True)
		employee = frappe.get_doc(
			{
				"doctype": "Employee",
				"first_name": "Aina",
				"last_name": "Rahman",
				"employee_number": "MW-E2E-001",
				"company": company,
				"designation": designation,
				"gender": "Female",
				"date_of_birth": "1998-04-15",
				"date_of_joining": "2026-01-01",
				"status": "Inactive",
				"user_id": EMPLOYEE_EMAIL,
				"bank_ac_no": "123456789012",
			}
		).insert(ignore_permissions=True).name
	if not frappe.db.exists("Malaysia Employee Profile", {"employee": employee}):
		frappe.get_doc(
			{
				"doctype": "Malaysia Employee Profile",
				"employee": employee,
				"company": company,
				"effective_from": "2026-01-01",
				"nationality_status": "Malaysian",
				"nric_number": "980415140001",
				"tax_regime": "STANDARD",
				"tax_category": "1",
				"child_units": 0,
				"epf_number": "10000001",
				"socso_number": "980415140001",
				"eis_number": "980415140001",
				"income_tax_number": "IG123456780",
			}
		).insert(ignore_permissions=True)
	else:
		frappe.db.set_value(
			"Malaysia Employee Profile",
			frappe.db.get_value("Malaysia Employee Profile", {"employee": employee}, "name"),
			{"eis_number": "980415140001"},
			update_modified=False,
		)
	if not frappe.db.exists("Employee Work Agreement", {"employee": employee}):
		frappe.get_doc(
			{
				"doctype": "Employee Work Agreement",
				"employee": employee,
				"company": company,
				"effective_from": "2026-01-01",
				"work_arrangement": "Casual",
				"contract_relationship": "Contract of Service",
				"regularity": "Occasional or Irregular",
				"jurisdiction": "Peninsular Malaysia",
				"pay_basis": "Hourly",
				"base_hourly_rate": 15,
				"comparable_full_time_daily_hours": 8,
				"comparable_full_time_weekly_hours": 45,
				"maximum_daily_hours": 12,
				"maximum_weekly_hours": 45,
				"minimum_shift_hours": 2,
				"weekly_rest_day": "Sunday",
			}
		).insert(ignore_permissions=True)
	if not frappe.db.exists("Statutory Coverage Profile", {"employee": employee}):
		frappe.get_doc(
			{
				"doctype": "Statutory Coverage Profile",
				"employee": employee,
				"company": company,
				"effective_from": "2026-01-01",
			}
		).insert(ignore_permissions=True)
	doc = frappe.get_doc("Employee", employee)
	doc.status = "Active"
	doc.designation = designation
	doc.save(ignore_permissions=True)
	return employee


def _configure_kiosk(employee: str) -> None:
	settings = frappe.get_doc("Malaysia Workforce Settings")
	settings.kiosk_enabled = 1
	settings.kiosk_device_id = KIOSK_ID
	settings.kiosk_shared_secret = KIOSK_SECRET
	settings.kiosk_max_clock_drift_seconds = 300
	settings.prevent_consecutive_same_checkin_type = 1
	settings.auto_submit_verified_work_records = 0
	settings.save(ignore_permissions=True)
	frappe.clear_cache(doctype="Malaysia Workforce Settings")
	set_kiosk_credential(employee, KIOSK_CREDENTIAL)


def _signature(event_id: str, employee: str, log_type: str, timestamp) -> str:
	payload = "|".join((event_id, KIOSK_ID, employee, log_type, str(timestamp)))
	return hmac.new(KIOSK_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()


def _ensure_staffing_plan(company: str, employee: str, designation: str):
	cycle_start = getdate()
	start_time, end_time = time(8), time(12)
	# Browser and live-suite runs can cross midnight. Reuse the already published
	# deterministic scenario instead of manufacturing a second operational cycle.
	plan_name = frappe.db.get_value(
		"Cafe Staffing Plan",
		{"company": company, "plan_title": "MW E2E Two-week Staffing Plan", "workflow_state": "Approved"},
		"name",
	)
	if plan_name:
		return frappe.get_doc("Cafe Staffing Plan", plan_name)
	template_name = frappe.db.get_value("Cafe Coverage Template", {"template_name": "MW E2E Standard Coverage"}, "name")
	if not template_name:
		template_name = frappe.get_doc(
			{
				"doctype": "Cafe Coverage Template",
				"template_name": "MW E2E Standard Coverage",
				"company": company,
				"effective_from": cycle_start,
				"effective_until": add_days(cycle_start, 13),
				"coverage_rows": [
					{
						"weekday": cycle_start.strftime("%A"),
						"start_time": start_time,
						"end_time": end_time,
						"required_headcount": 1,
						"designation": designation,
						"criticality": "Critical",
					}
				],
			}
		).insert(ignore_permissions=True).name
	plan = frappe.get_doc(
		{
			"doctype": "Cafe Staffing Plan",
			"plan_title": "MW E2E Two-week Staffing Plan",
			"company": company,
			"manager": HR_MANAGER_EMAIL,
			"cycle_start": cycle_start,
			"coverage_template": template_name,
		}
	).insert(ignore_permissions=True)
	plan = apply_workflow(plan.as_dict(), "Open Availability")
	availability = frappe.get_doc(
		{
			"doctype": "Casual Availability",
			"employee": employee,
			"company": company,
			"cycle_start": cycle_start,
			"amendment_reason": "Isolated E2E setup for today's operational shift.",
			"availability_windows": [
				{"work_date": cycle_start, "available_from": start_time, "available_until": end_time},
				{"work_date": add_days(cycle_start, 7), "available_from": start_time, "available_until": end_time},
			],
		}
	).insert(ignore_permissions=True)
	if availability.manager_review_status == "Pending":
		frappe.set_user(HR_MANAGER_EMAIL)
		availability = apply_workflow(availability.as_dict(), "Approve")
		frappe.set_user("Administrator")
	plan = apply_workflow(plan.as_dict(), "Generate Proposal")
	frappe.set_user(HR_MANAGER_EMAIL)
	approved = apply_workflow(plan.as_dict(), "Approve and Publish")
	frappe.set_user("Administrator")
	approved.reload()
	return approved


def _ensure_attendance(employee: str, assignment, work_record):
	shift = frappe.db.get_value("Shift Assignment", assignment, "shift_type")
	name = frappe.db.get_value(
		"Attendance", {"employee": employee, "attendance_date": work_record.work_date, "docstatus": 1}, "name"
	)
	if name:
		return name
	doc = frappe.get_doc(
		{
			"doctype": "Attendance",
			"employee": employee,
			"attendance_date": work_record.work_date,
			"company": work_record.company,
			"status": "Present",
			"shift": shift,
		}
	).insert(ignore_permissions=True)
	doc.submit()
	return doc.name


def _exercise_kiosk(employee: str, assignment: str):
	work_record_name = frappe.db.get_value("Shift Assignment", assignment, "custom_shift_work_record")
	work_record = frappe.get_doc("Shift Work Record", work_record_name)
	start, end = work_record.scheduled_start, work_record.scheduled_end
	results = []
	for log_type, timestamp in (("IN", start), ("OUT", end)):
		event_id = f"MW-E2E-{log_type}-{work_record.name}"
		results.append(
			kiosk_clock(
				event_id=event_id,
				kiosk_id=KIOSK_ID,
				employee=employee,
				credential=KIOSK_CREDENTIAL,
				log_type=log_type,
				device_timestamp=str(timestamp),
				signature=_signature(event_id, employee, log_type, timestamp),
				offline_queued=1,
			)
		)
	duplicate_id = f"MW-E2E-IN-{work_record.name}"
	duplicate = kiosk_clock(
		event_id=duplicate_id,
		kiosk_id=KIOSK_ID,
		employee=employee,
		credential=KIOSK_CREDENTIAL,
		log_type="IN",
		device_timestamp=str(start),
		signature=_signature(duplicate_id, employee, "IN", start),
		offline_queued=1,
	)
	work_record.reload()
	attendance = _ensure_attendance(employee, assignment, work_record)
	if work_record.docstatus == 0:
		work_record.submit()
	return work_record, attendance, [row["name"] for row in results], duplicate


def _ensure_payroll_setup(company: str, employee: str, from_date) -> tuple[str, str]:
	if frappe.db.exists("Fiscal Year", "2026"):
		fiscal_year = frappe.get_doc("Fiscal Year", "2026")
		if company not in {row.company for row in fiscal_year.companies}:
			fiscal_year.append("companies", {"company": company})
			fiscal_year.save(ignore_permissions=True)
	else:
		frappe.get_doc(
			{
				"doctype": "Fiscal Year",
				"year": "2026",
				"year_start_date": "2026-01-01",
				"year_end_date": "2026-12-31",
				"companies": [{"company": company}],
			}
		).insert(ignore_permissions=True)
	holiday_list = "MW E2E Malaysia 2026"
	if not frappe.db.exists("Holiday List", holiday_list):
		frappe.get_doc(
			{
				"doctype": "Holiday List",
				"holiday_list_name": holiday_list,
				"from_date": "2026-01-01",
				"to_date": "2026-12-31",
				"country": "Malaysia",
			}
		).insert(ignore_permissions=True)
	frappe.db.set_value("Company", company, "default_holiday_list", holiday_list, update_modified=False)
	frappe.clear_cache(doctype="Company")
	if not frappe.db.exists(
		"Holiday List Assignment",
		{
			"holiday_list": holiday_list,
			"applicable_for": "Company",
			"assigned_to": company,
			"docstatus": 1,
		},
	):
		holiday_assignment = frappe.get_doc(
			{
				"doctype": "Holiday List Assignment",
				"naming_series": "HR-HLA-.YYYY.-",
				"holiday_list": holiday_list,
				"applicable_for": "Company",
				"assigned_to": company,
				"from_date": "2026-01-01",
			}
		).insert(ignore_permissions=True)
		holiday_assignment.submit()
	payable_account = frappe.db.get_value(
		"Account",
		{"company": company, "account_type": "Payable", "root_type": "Liability", "is_group": 0},
		"name",
	)
	if not payable_account:
		frappe.throw("The isolated payroll scenario requires a non-group payable account.")
	expense_account = frappe.db.get_value(
		"Account",
		{"company": company, "account_name": "Salary", "root_type": "Expense", "is_group": 0},
		"name",
	)
	if not expense_account:
		frappe.throw("The isolated payroll scenario requires a non-group salary expense account.")
	for component_name, account in {
		"Casual Ordinary Pay": expense_account,
		"EPF Employee": payable_account,
		"SOCSO Employee": payable_account,
		"SKBBK Employee": payable_account,
		"EIS Employee": payable_account,
		"PCB": payable_account,
	}.items():
		component = frappe.get_doc("Salary Component", component_name)
		if company not in {row.company for row in component.accounts}:
			component.append("accounts", {"company": company, "account": account})
			component.save(ignore_permissions=True)
	structure_name = "MW E2E Casual Fortnightly"
	if not frappe.db.exists("Salary Structure", structure_name):
		structure = frappe.new_doc("Salary Structure")
		structure.name = structure_name
		structure.company = company
		structure.is_active = "Yes"
		structure.payroll_frequency = "Fortnightly"
		structure.currency = "MYR"
		structure.append("earnings", {"salary_component": "Casual Ordinary Pay", "amount": 0})
		structure.insert(ignore_permissions=True)
		structure.submit()
	assignment = frappe.db.get_value(
		"Salary Structure Assignment",
		{
			"employee": employee,
			"salary_structure": structure_name,
			"company": company,
			"docstatus": 1,
		},
		"name",
	)
	if not assignment:
		doc = frappe.new_doc("Salary Structure Assignment")
		doc.employee = employee
		doc.salary_structure = structure_name
		doc.company = company
		doc.from_date = from_date
		doc.base = 0
		doc.currency = "MYR"
		doc.payroll_payable_account = payable_account
		doc.insert(ignore_permissions=True)
		doc.submit()
	return structure_name, payable_account


def exercise_payroll_uat(*, commit: bool = False) -> dict:
	"""Run standard HRMS payroll through a deterministic UAT-only bank artifact."""
	frappe.set_user("Administrator")
	record_row = frappe.get_all(
		"Shift Work Record",
		filters={
			"company": COMPANY,
			"docstatus": 1,
			"status": ["in", ["Approved", "Automatically Verified", "Payroll Generated"]],
		},
		fields=["name", "employee", "staffing_plan"],
		order_by="work_date asc, name asc",
		limit=1,
	)
	if not record_row:
		seed_demo()
		record_row = frappe.get_all(
			"Shift Work Record",
			filters={"company": COMPANY, "docstatus": 1},
			fields=["name", "employee", "staffing_plan"],
			order_by="work_date asc, name asc",
			limit=1,
		)
	record = record_row[0]
	plan = frappe.get_doc("Cafe Staffing Plan", record.staffing_plan)
	profile_name = frappe.db.get_value("Malaysia Employee Profile", {"employee": record.employee}, "name")
	frappe.db.set_value(
		"Malaysia Employee Profile",
		profile_name,
		{"eis_number": "980415140001"},
		update_modified=False,
	)
	_, payable_account = _ensure_payroll_setup(COMPANY, record.employee, plan.cycle_start)

	entry_name = frappe.db.get_value(
		"Payroll Entry",
		{
			"company": COMPANY,
			"start_date": plan.cycle_start,
			"end_date": plan.cycle_end,
			"custom_malaysia_enabled": 1,
			"docstatus": ["<", 2],
		},
		"name",
	)
	frappe.set_user(PAYROLL_EMAIL)
	if entry_name:
		entry = frappe.get_doc("Payroll Entry", entry_name)
	else:
		entry = frappe.new_doc("Payroll Entry")
		entry.company = COMPANY
		entry.posting_date = plan.cycle_end
		entry.payroll_frequency = "Fortnightly"
		entry.start_date = plan.cycle_start
		entry.end_date = plan.cycle_end
		entry.cost_center = "Main - MWC"
		entry.currency = "MYR"
		entry.exchange_rate = 1
		entry.payroll_payable_account = payable_account
		entry.custom_malaysia_enabled = 1
		entry.insert()
		entry_name = entry.name

	from malaysia_workforce.banking.service import prepare_bank_file, release_payroll
	from malaysia_workforce.payroll.services import prepare_payroll_entry

	prepared = None
	if entry.docstatus == 0 and entry.custom_malaysia_control_state != "Validated":
		prepared = prepare_payroll_entry(entry.name)
		if prepared["status"] != "Validated":
			frappe.throw(f"Isolated payroll validation failed: {prepared}")
	for name in frappe.get_all(
		"Additional Salary",
		filters={"ref_doctype": "Payroll Entry", "ref_docname": entry.name, "docstatus": 0},
		pluck="name",
	):
		frappe.get_doc("Additional Salary", name).submit()
	entry.reload()
	if entry.docstatus == 0:
		entry.submit()
	entry.reload()
	if frappe.db.exists("Salary Slip", {"payroll_entry": entry.name, "docstatus": 0}):
		entry.submit_salary_slips()
	entry.reload()
	bank = prepare_bank_file(entry.name)
	frappe.set_user(RELEASER_EMAIL)
	release_blocked = False
	try:
		release_payroll(entry.name)
	except frappe.ValidationError:
		release_blocked = True
	finally:
		frappe.set_user("Administrator")
	result = {
		"payroll_entry": entry.name,
		"prepared": prepared,
		"salary_slips": frappe.get_all(
			"Salary Slip",
			filters={"payroll_entry": entry.name, "docstatus": 1},
			pluck="name",
		),
		"bank": bank,
		"release_blocked_without_activation": release_blocked,
	}
	if commit:
		frappe.db.commit()
	return result


def seed_demo(*, commit: bool = False) -> dict:
	"""Seed native staffing, shifts, kiosk evidence, Attendance, and derived pay."""
	frappe.set_user("Administrator")
	company = _ensure_company()
	_ensure_user(EMPLOYEE_EMAIL, "Aina", ("Employee", "Casual Employee"), "employee-e2e")
	_ensure_user(HR_MANAGER_EMAIL, "Maya", ("HR Manager", "Malaysia HR Manager", "Outlet Manager"), "manager-e2e")
	_ensure_user(PAYROLL_EMAIL, "Priya", ("Malaysia Payroll User",), "payroll-e2e")
	_ensure_user(RELEASER_EMAIL, "Hana", ("Malaysia HR Manager",), "releaser-e2e")
	_ensure_user(AUDITOR_EMAIL, "Adam", ("Malaysia Workforce Auditor",), "auditor-e2e")
	for user in (HR_MANAGER_EMAIL, PAYROLL_EMAIL, RELEASER_EMAIL, AUDITOR_EMAIL):
		_ensure_company_permission(user, company)
	designation, _ = _ensure_designation_and_shift()
	employee = _ensure_employee(company, designation)
	_configure_kiosk(employee)
	plan = _ensure_staffing_plan(company, employee, designation)
	assignment = next(row.shift_assignment for row in plan.recommendations if row.shift_assignment)
	work_record, attendance, checkins, duplicate = _exercise_kiosk(employee, assignment)
	result = {
		"company": company,
		"employee": employee,
		"employee_user": EMPLOYEE_EMAIL,
		"hr_manager_user": HR_MANAGER_EMAIL,
		"payroll_user": PAYROLL_EMAIL,
		"releaser_user": RELEASER_EMAIL,
		"auditor_user": AUDITOR_EMAIL,
		"staffing_plan": plan.name,
		"published": {"status": plan.workflow_state},
		"shift_assignment": assignment,
		"attendance": attendance,
		"work_record": work_record.name,
		"work_record_status": work_record.status,
		"work_record_docstatus": work_record.docstatus,
		"gross_pay": work_record.gross_pay,
		"checkins": checkins,
		"duplicate": duplicate,
		"shift_start": work_record.scheduled_start,
		"shift_end": work_record.scheduled_end,
	}
	if commit:
		frappe.db.commit()
	return result
