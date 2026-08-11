from __future__ import annotations

import frappe
from frappe import _

ROLES = (
	"Casual Employee",
	"Outlet Manager",
	"Malaysia Payroll User",
	"Malaysia HR Manager",
	"Malaysia Kiosk",
	"Statutory Administrator",
	"Malaysia Workforce Auditor",
)

AUDITOR_DOCTYPES = (
	"Company",
	"Employee",
	"Casual Availability",
	"Cafe Coverage Template",
	"Cafe Staffing Plan",
	"Shift Assignment",
	"Employee Checkin",
	"Attendance",
	"Shift Work Record",
	"Payroll Entry",
	"Salary Slip",
	"Additional Salary",
	"Journal Entry",
	"Employee Work Agreement",
	"Malaysia Employee Profile",
	"Statutory Coverage Profile",
	"Malaysia Tax Declaration TP1",
	"Malaysia Previous Employment TP3",
	"Monthly Statutory Accumulator",
	"Statutory Submission",
	"Malaysia Employee Notification",
	"Malaysia Annual Remuneration Statement",
	"Statutory Treatment History",
	"ToDo",
	"Issue",
	"Training Event",
	"Malaysia Workforce Settings",
)

STANDARD_ROLE_PERMISSIONS = {
	"Outlet Manager": {
		name: {"read": 1, "select": 1, "report": 1}
		for name in (
			"Company",
			"Employee",
			"Designation",
			"Branch",
			"Shift Location",
			"Skill",
			"Shift Type",
			"Shift Assignment",
		)
	},
	"Malaysia Payroll User": {
		"Payroll Entry": {"read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1, "delete": 1, "report": 1, "share": 1},
		"Salary Slip": {"read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1, "delete": 1, "amend": 1, "report": 1, "share": 1, "print": 1, "email": 1},
		"Additional Salary": {"read": 1, "write": 1, "create": 1, "submit": 1, "report": 1, "share": 1, "print": 1, "email": 1},
		**{
			name: {"read": 1, "select": 1, "report": 1}
			for name in (
				"Company",
				"Employee",
				"Salary Structure",
				"Salary Structure Assignment",
				"Salary Component",
				"Payroll Period",
				"Journal Entry",
			)
		},
	},
	"Malaysia HR Manager": {
		name: {"read": 1, "select": 1, "report": 1, "print": 1}
		for name in ("Company", "Employee", "Payroll Entry", "Salary Slip", "Journal Entry")
	},
	"Statutory Administrator": {
		name: {"read": 1, "select": 1, "report": 1, "print": 1}
		for name in ("Company", "Employee", "Payroll Entry", "Salary Slip")
	},
}

EMPLOYMENT_TYPES = ("Part Time", "Casual", "Temporary", "Seasonal")

COMPONENTS = {
	"Casual Ordinary Pay": {"abbr": "COP", "type": "Earning", "epf": 1, "socso": 1, "eis": 1, "hrd": 1, "pcb": 1, "pcb_type": "Regular Remuneration"},
	"Part-Time Additional Hours": {"abbr": "PTAH", "type": "Earning", "epf": 1, "socso": 1, "eis": 1, "hrd": 1, "pcb": 1, "pcb_type": "Regular Remuneration"},
	"Casual Overtime Pay": {"abbr": "COT", "type": "Earning", "epf": 0, "socso": 1, "eis": 1, "pcb": 1, "pcb_type": "Additional Remuneration"},
	"Rest Day Pay": {"abbr": "RDP", "type": "Earning", "epf": 0, "socso": 1, "eis": 1, "pcb": 1, "pcb_type": "Additional Remuneration"},
	"Public Holiday Pay": {"abbr": "PHP", "type": "Earning", "epf": 1, "socso": 1, "eis": 1, "pcb": 1, "pcb_type": "Additional Remuneration"},
	"Shift Allowance": {"abbr": "SHA", "type": "Earning", "epf": 1, "socso": 1, "eis": 1, "hrd": 1, "pcb": 1, "pcb_type": "Regular Remuneration"},
	"Meal Allowance": {"abbr": "MEA", "type": "Earning", "epf": 1, "socso": 1, "eis": 1, "pcb": 1, "pcb_type": "Regular Remuneration"},
	"Travel Allowance": {"abbr": "TRA", "type": "Earning", "epf": 1, "socso": 1, "eis": 1, "pcb": 1, "pcb_type": "Regular Remuneration"},
	"EPF Employee": {"abbr": "EPFE", "type": "Deduction"},
	"SOCSO Employee": {"abbr": "SOC", "type": "Deduction"},
	"SKBBK Employee": {"abbr": "SKB", "type": "Deduction"},
	"EIS Employee": {"abbr": "EIS", "type": "Deduction"},
	"PCB": {"abbr": "PCB", "type": "Deduction"},
	"CP38": {"abbr": "CP38", "type": "Deduction"},
	"Zakat": {"abbr": "ZAK", "type": "Deduction"},
}


def create_master_data():
	for role in ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc(
				{
					"doctype": "Role",
					"role_name": role,
					"desk_access": 0 if role in {"Casual Employee", "Malaysia Kiosk"} else 1,
				}
			).insert(ignore_permissions=True)
	for employment_type in EMPLOYMENT_TYPES:
		if not frappe.db.exists("Employment Type", employment_type):
			frappe.get_doc(
				{"doctype": "Employment Type", "employee_type_name": employment_type}
			).insert(ignore_permissions=True)
	create_salary_components()
	_create_print_formats()
	_create_staffing_workflow()
	_create_availability_review_workflow()
	_create_standard_role_permissions()
	_create_auditor_permissions()


def _create_standard_role_permissions():
	"""Grant each separated workforce role only the Frappe/HRMS records it operates."""
	from frappe.permissions import setup_custom_perms

	for role, doctypes in STANDARD_ROLE_PERMISSIONS.items():
		for doctype, rights in doctypes.items():
			if not frappe.db.exists("DocType", doctype):
				continue
			if not frappe.db.exists("Custom DocPerm", {"parent": doctype}):
				# This is the supported Permission Manager path and keeps the complete
				# upstream permission matrix before our narrow role row is added.
				setup_custom_perms(doctype)
			name = frappe.db.get_value(
				"Custom DocPerm",
				{"parent": doctype, "role": role, "permlevel": 0, "if_owner": 0},
				"name",
			)
			values = {"select": 1, **rights}
			if name:
				frappe.db.set_value("Custom DocPerm", name, values, update_modified=False)
				continue
			frappe.get_doc(
				{
					"doctype": "Custom DocPerm",
					"parent": doctype,
					"parenttype": "DocType",
					"parentfield": "permissions",
					"role": role,
					"permlevel": 0,
					**values,
				}
			).insert(ignore_permissions=True)


def _create_auditor_permissions():
	"""Add a read-only standard Frappe role without duplicating app records."""
	from frappe.permissions import setup_custom_perms

	role = "Malaysia Workforce Auditor"
	for doctype in AUDITOR_DOCTYPES:
		if not frappe.db.exists("DocType", doctype):
			continue
		custom_rows = frappe.get_all(
			"Custom DocPerm", filters={"parent": doctype}, fields=["name", "role", "permlevel"]
		)
		if not custom_rows:
			# Frappe's supported Permission Manager path first copies standard DocPerm
			# rows; otherwise adding one custom role would hide every standard role.
			setup_custom_perms(doctype)
		elif {row.role for row in custom_rows} == {role}:
			# Repair sites migrated through the short-lived pre-release RC6 build that
			# created the auditor row before copying the standard permission matrix.
			for standard in frappe.get_all("DocPerm", filters={"parent": doctype}, fields="*"):
				if frappe.db.exists(
					"Custom DocPerm",
					{
						"parent": doctype,
						"role": standard.role,
						"permlevel": standard.permlevel,
						"if_owner": standard.if_owner,
					},
				):
					continue
				copy = frappe.new_doc("Custom DocPerm")
				copy.update(standard)
				copy.name = None
				copy.insert(ignore_permissions=True)
		if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0}):
			continue
		frappe.get_doc(
			{
				"doctype": "Custom DocPerm",
				"parent": doctype,
				"role": role,
				"permlevel": 0,
				"select": 1,
				"read": 1,
				"report": 1,
				"export": 1,
				"print": 1,
			}
		).insert(ignore_permissions=True)


def create_salary_components():
	"""Create settings-linked components before singleton defaults are initialised."""
	for name, values in COMPONENTS.items():
		_create_or_update_component(name, values)


def _create_or_update_component(name: str, values: dict):
	expected_type = values["type"]
	exists = bool(frappe.db.exists("Salary Component", name))
	doc = frappe.get_doc("Salary Component", name) if exists else frappe.new_doc("Salary Component")

	if exists and doc.type != expected_type:
		frappe.throw(
			_(
				"Salary Component {0} already exists with type {1}; Malaysia Workforce requires type {2}. "
				"Rename the existing component or resolve the conflict before installing."
			).format(frappe.bold(name), frappe.bold(doc.type), frappe.bold(expected_type)),
			title=_("Reserved Salary Component Conflict"),
		)

	if exists and not int(doc.get("custom_malaysia_component") or 0):
		frappe.throw(
			_(
				"Salary Component {0} already exists but is not managed by Malaysia Workforce. "
				"Rename it or explicitly migrate it after reviewing its formulas, accounts and statutory classification."
			).format(frappe.bold(name)),
			title=_("Reserved Salary Component Conflict"),
		)

	if exists:
		# Never overwrite payroll formulas, account mappings, abbreviations or statutory
		# wage classifications during migrate. Administrators may intentionally tune
		# these effective settings for their own remuneration policies.
		return

	doc.salary_component = name
	doc.type = expected_type
	doc.salary_component_abbr = values["abbr"]
	doc.depends_on_payment_days = 0
	doc.remove_if_zero_valued = 1
	doc.custom_malaysia_component = 1
	doc.custom_include_in_epf_wages = int(values.get("epf", 0)) if expected_type == "Earning" else 0
	doc.custom_include_in_socso_wages = int(values.get("socso", 0)) if expected_type == "Earning" else 0
	doc.custom_include_in_eis_wages = int(values.get("eis", 0)) if expected_type == "Earning" else 0
	doc.custom_include_in_pcb_remuneration = int(values.get("pcb", 0)) if expected_type == "Earning" else 0
	doc.custom_pcb_remuneration_type = values.get("pcb_type", "") if expected_type == "Earning" else ""
	doc.custom_include_in_lindung_wages = 0
	doc.custom_include_in_hrd_levy_wages = int(values.get("hrd", 0)) if expected_type == "Earning" else 0
	if expected_type == "Deduction":
		doc.custom_malaysia_deduction_basis = (
			"Employee Written Request" if name == "Zakat" else "Written Law"
		)
	doc.variable_based_on_taxable_salary = 0
	doc.statistical_component = 0
	doc.do_not_include_in_total = 0
	doc.do_not_include_in_accounts = 0
	doc.accrual_component = 0
	doc.is_flexible_benefit = 0
	doc.deduct_full_tax_on_selected_payroll_date = 0
	doc.is_tax_applicable = int(values.get("pcb", 0)) if expected_type == "Earning" else 0
	doc.insert(ignore_permissions=True)


def _create_print_formats():
	from malaysia_workforce.setup.print_formats import PRINT_FORMATS

	for name, definition in PRINT_FORMATS.items():
		if frappe.db.exists("Print Format", name):
			doc = frappe.get_doc("Print Format", name)
			if doc.module != "Malaysia Workforce" or doc.doc_type != definition["doctype"]:
				frappe.throw(
					_(
						"Print Format {0} is reserved by Malaysia Workforce but already belongs to module {1} "
						"or another DocType. Rename the existing format before installing."
					).format(frappe.bold(name), frappe.bold(doc.module or _("Unknown"))),
					title=_("Reserved Print Format Conflict"),
				)
		else:
			doc = frappe.new_doc("Print Format")
			doc.name = name
			doc.print_format_name = name

		doc.doc_type = definition["doctype"]
		doc.module = "Malaysia Workforce"
		doc.print_format_type = "Jinja"
		doc.custom_format = 1
		doc.disabled = 0
		doc.html = definition["html"]
		if doc.is_new():
			doc.insert(ignore_permissions=True)
		else:
			doc.save(ignore_permissions=True)


def _create_staffing_workflow():
	"""Install the planning approval as a standard Frappe Workflow."""
	states = {
		"Draft": "",
		"Collecting Availability": "Info",
		"Proposed": "Warning",
		"Approved": "Success",
		"Superseded": "Inverse",
	}
	actions = (
		"Open Availability",
		"Generate Proposal",
		"Revise",
		"Approve and Publish",
		"Supersede",
	)
	for name, style in states.items():
		if not frappe.db.exists("Workflow State", name):
			frappe.get_doc(
				{"doctype": "Workflow State", "workflow_state_name": name, "style": style}
			).insert(ignore_permissions=True)
	for name in actions:
		if not frappe.db.exists("Workflow Action Master", name):
			frappe.get_doc(
				{"doctype": "Workflow Action Master", "workflow_action_name": name}
			).insert(ignore_permissions=True)

	name = "Cafe Staffing Plan Approval"
	workflow = frappe.get_doc("Workflow", name) if frappe.db.exists("Workflow", name) else frappe.new_doc("Workflow")
	workflow.workflow_name = name
	workflow.document_type = "Cafe Staffing Plan"
	workflow.workflow_state_field = "workflow_state"
	workflow.is_active = 1
	workflow.send_email_alert = 0
	workflow.enable_action_confirmation = 1
	workflow.set("states", [])
	workflow.append("states", {"state": "Draft", "doc_status": "0", "allow_edit": "All"})
	workflow.append("states", {"state": "Collecting Availability", "doc_status": "0", "allow_edit": "All"})
	workflow.append("states", {"state": "Proposed", "doc_status": "0", "allow_edit": "All"})
	workflow.append("states", {"state": "Approved", "doc_status": "1", "allow_edit": "All"})
	workflow.append("states", {"state": "Superseded", "doc_status": "1", "allow_edit": "All"})
	workflow.set("transitions", [])
	for state, action, next_state in (
		("Draft", "Open Availability", "Collecting Availability"),
		("Collecting Availability", "Generate Proposal", "Proposed"),
		("Proposed", "Revise", "Collecting Availability"),
		("Proposed", "Approve and Publish", "Approved"),
		("Approved", "Supersede", "Superseded"),
	):
		roles = (
			("HR Manager", "Malaysia HR Manager", "System Manager")
			if action in {"Approve and Publish", "Supersede"}
			else ("Outlet Manager", "HR Manager", "Malaysia HR Manager", "System Manager")
		)
		for role in roles:
			workflow.append(
				"transitions",
				{
					"state": state,
					"action": action,
					"next_state": next_state,
					"allowed": role,
					"allow_self_approval": 0 if action == "Approve and Publish" else 1,
				},
			)
	if workflow.is_new():
		workflow.insert(ignore_permissions=True)
	else:
		workflow.save(ignore_permissions=True)


def _create_availability_review_workflow():
	"""Use native Workflow actions for late availability review."""
	for name, style in {"Draft": "", "Approved": "Success", "Rejected": "Danger"}.items():
		if not frappe.db.exists("Workflow State", name):
			frappe.get_doc(
				{"doctype": "Workflow State", "workflow_state_name": name, "style": style}
			).insert(ignore_permissions=True)
	for action in ("Approve", "Reject"):
		if not frappe.db.exists("Workflow Action Master", action):
			frappe.get_doc(
				{"doctype": "Workflow Action Master", "workflow_action_name": action}
			).insert(ignore_permissions=True)
	name = "Casual Availability Late Review"
	workflow = frappe.get_doc("Workflow", name) if frappe.db.exists("Workflow", name) else frappe.new_doc("Workflow")
	workflow.workflow_name = name
	workflow.document_type = "Casual Availability"
	workflow.workflow_state_field = "workflow_state"
	workflow.is_active = 1
	workflow.send_email_alert = 0
	workflow.enable_action_confirmation = 1
	workflow.set("states", [])
	for state, editable in (
		("Draft", "Employee"),
		("Approved", "Outlet Manager"),
		("Rejected", "Outlet Manager"),
	):
		workflow.append("states", {"state": state, "doc_status": "0", "allow_edit": editable})
	workflow.set("transitions", [])
	for role in ("Outlet Manager", "HR Manager", "Malaysia HR Manager", "System Manager"):
		for action, next_state in (("Approve", "Approved"), ("Reject", "Rejected")):
			workflow.append(
				"transitions",
				{
					"state": "Draft",
					"action": action,
					"next_state": next_state,
					"allowed": role,
					"allow_self_approval": 0,
					"condition": "doc.late_amendment == 1",
				},
			)
	if workflow.is_new():
		workflow.insert(ignore_permissions=True)
	else:
		workflow.save(ignore_permissions=True)
