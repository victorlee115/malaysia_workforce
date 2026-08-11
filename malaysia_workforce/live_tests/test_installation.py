from __future__ import annotations

import frappe
from frappe.tests import IntegrationTestCase

from malaysia_workforce import hooks as mw_hooks
from malaysia_workforce.setup.master_data import (
	AUDITOR_DOCTYPES,
	COMPONENTS,
	ROLES,
	STANDARD_ROLE_PERMISSIONS,
)
from malaysia_workforce.setup.print_formats import PRINT_FORMATS


class TestMalaysiaWorkforceInstallation(IntegrationTestCase):
	def test_required_apps_and_custom_doctypes_are_installed(self):
		installed = set(frappe.get_installed_apps())
		self.assertTrue({"frappe", "erpnext", "hrms", "malaysia_workforce"} <= installed)
		for doctype in (
			"Casual Availability",
			"Cafe Coverage Template",
			"Cafe Staffing Plan",
			"Shift Work Record",
			"Statutory Coverage Profile",
			"Statutory Submission",
		):
			self.assertTrue(frappe.db.exists("DocType", doctype), doctype)

	def test_standard_doctype_extensions_exist(self):
		required_fields = {
			"Employee": ("custom_staffing_priority", "custom_staffing_priority_effective_from", "custom_malaysia_employee_profile", "custom_malaysia_privacy_acknowledgement"),
			"Company": ("custom_enable_malaysia_payroll", "custom_hrd_corp_registration_number", "custom_malaysia_rule_review_deadline", "custom_malaysia_privacy_notice", "custom_malaysia_last_backup_on"),
			"Salary Component": ("custom_malaysia_component", "custom_include_in_hrd_levy_wages", "custom_malaysia_deduction_basis"),
			"Shift Assignment": ("custom_malaysia_staffing_plan", "custom_malaysia_staffing_recommendation_key", "custom_shift_work_record"),
			"Employee Checkin": ("custom_kiosk_event_id", "custom_device_timestamp", "custom_server_received_timestamp", "custom_malaysia_correction_pair_id", "custom_malaysia_correction_status"),
			"Salary Slip": ("custom_malaysia_payroll_entry", "custom_malaysia_statutory_snapshot"),
			"Payroll Entry": ("custom_malaysia_control_state", "custom_malaysia_source_snapshot_hash", "custom_malaysia_work_record_reservation_status", "custom_malaysia_processed_by", "custom_malaysia_employer_contribution_journal", "custom_malaysia_employer_contribution_total", "custom_malaysia_bank_file_hash", "custom_malaysia_statutory_preparation_status"),
			"ToDo": ("custom_malaysia_exception_code", "custom_malaysia_resolution_hash"),
			"Issue": ("custom_malaysia_workplace_incident", "custom_perkeso_escalation_due"),
		}
		for doctype, fields in required_fields.items():
			meta = frappe.get_meta(doctype)
			for fieldname in fields:
				self.assertTrue(meta.has_field(fieldname), f"{doctype}.{fieldname}")

	def test_managed_roles_components_and_print_formats_exist(self):
		for role in ROLES:
			self.assertTrue(frappe.db.exists("Role", role), role)
		for doctype in AUDITOR_DOCTYPES:
			self.assertTrue(
				frappe.db.exists(
					"Custom DocPerm",
					{"parent": doctype, "role": "Malaysia Workforce Auditor", "permlevel": 0, "read": 1, "write": 0},
				),
				doctype,
			)
		for role, doctypes in STANDARD_ROLE_PERMISSIONS.items():
			for doctype, rights in doctypes.items():
				if not frappe.db.exists("DocType", doctype):
					continue
				row = frappe.db.get_value(
					"Custom DocPerm",
					{"parent": doctype, "role": role, "permlevel": 0, "if_owner": 0},
					["name", *rights],
					as_dict=True,
				)
				self.assertIsNotNone(row, f"{role}: {doctype}")
				for right, expected in rights.items():
					self.assertEqual(int(row.get(right) or 0), expected, f"{role}: {doctype}.{right}")
		for component, definition in COMPONENTS.items():
			row = frappe.db.get_value(
				"Salary Component",
				component,
				["type", "custom_malaysia_component"],
				as_dict=True,
			)
			self.assertIsNotNone(row, component)
			self.assertEqual(row.type, definition["type"])
			self.assertEqual(int(row.custom_malaysia_component or 0), 1)
		for name, definition in PRINT_FORMATS.items():
			row = frappe.db.get_value("Print Format", name, ["doc_type", "module"], as_dict=True)
			self.assertIsNotNone(row, name)
			self.assertEqual(row.doc_type, definition["doctype"])
			self.assertEqual(row.module, "Malaysia Workforce")
		workflow = frappe.get_doc("Workflow", "Cafe Staffing Plan Approval")
		approval_rows = [row for row in workflow.transitions if row.action == "Approve and Publish"]
		self.assertTrue(approval_rows)
		self.assertTrue(all(not row.allow_self_approval for row in approval_rows))
		self.assertNotIn("Outlet Manager", {row.allowed for row in approval_rows})

	def test_legacy_epf_export_is_disabled_by_default(self):
		settings = frappe.get_cached_doc("Malaysia Workforce Settings")
		self.assertEqual(int(settings.enable_legacy_epf_ecaruman_csv_for_uat or 0), 0)
		self.assertEqual(int(settings.auto_create_employer_contribution_journal or 0), 0)
		self.assertEqual(int(settings.auto_generate_statutory_files_on_final_run or 0), 0)

	def test_standard_hrms_records_are_the_public_owners(self):
		workspace = frappe.get_doc("Workspace", "Malaysia Workforce")
		self.assertTrue(
			any(row.link_to == "Payroll Entry" for row in workspace.shortcuts),
			"Malaysia Workforce must link to the standard Payroll Entry DocType",
		)
		self.assertTrue(any(row.link_to == "Cafe Staffing Plan" for row in workspace.shortcuts))
		self.assertFalse(frappe.db.exists("DocType", "Malaysia Payroll Run"))
		self.assertFalse(frappe.db.exists("DocType", "Casual Roster"))
		self.assertEqual(frappe.db.get_value("Role", "Malaysia Kiosk", "desk_access"), 0)
		self.assertFalse(getattr(mw_hooks, "override_doctype_class", None))
		self.assertFalse(getattr(mw_hooks, "add_to_apps_screen", None))

	def test_employee_availability_web_form_does_not_expose_identity_link(self):
		web_form = frappe.get_doc("Web Form", "casual-availability")
		self.assertNotIn("employee", {row.fieldname for row in web_form.web_form_fields})
		self.assertEqual(
			[row.fieldname for row in web_form.list_columns],
			["status", "cycle_start", "submitted_on"],
		)

	def test_hook_targets_resolve_on_live_site(self):
		def flatten(value):
			if isinstance(value, str):
				yield value
			elif isinstance(value, dict):
				for item in value.values():
					yield from flatten(item)
			elif isinstance(value, (list, tuple, set)):
				for item in value:
					yield from flatten(item)

		targets = {
			mw_hooks.before_install,
			mw_hooks.after_install,
			mw_hooks.after_migrate,
			mw_hooks.before_uninstall,
			"malaysia_workforce.statutory.submission_service.generate_submission_file",
		}
		for source in (
			mw_hooks.doc_events,
			mw_hooks.scheduler_events,
			mw_hooks.permission_query_conditions,
			mw_hooks.has_permission,
		):
			targets.update(item for item in flatten(source) if item.startswith("malaysia_workforce."))

		for target in sorted(targets):
			self.assertTrue(callable(frappe.get_attr(target)), target)
