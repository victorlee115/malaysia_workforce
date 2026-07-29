from __future__ import annotations

import frappe
from frappe.tests import IntegrationTestCase

from malaysia_workforce import hooks as mw_hooks
from malaysia_workforce.setup.master_data import COMPONENTS, ROLES
from malaysia_workforce.setup.print_formats import PRINT_FORMATS


class TestMalaysiaWorkforceInstallation(IntegrationTestCase):
	def test_required_apps_and_custom_doctypes_are_installed(self):
		installed = set(frappe.get_installed_apps())
		self.assertTrue({"frappe", "erpnext", "hrms", "malaysia_workforce"} <= installed)
		for doctype in (
			"Casual Roster",
			"Roster Application",
			"Roster Selection",
			"Shift Work Record",
			"Malaysia Payroll Run",
			"Statutory Coverage Profile",
			"Statutory Submission",
		):
			self.assertTrue(frappe.db.exists("DocType", doctype), doctype)

	def test_standard_doctype_extensions_exist(self):
		required_fields = {
			"Employee": ("custom_work_arrangement", "custom_roster_enabled", "custom_malaysia_employee_profile"),
			"Company": ("custom_enable_malaysia_payroll", "custom_epf_employer_number", "custom_socso_employer_code"),
			"Salary Component": ("custom_malaysia_component", "custom_include_in_epf_wages", "custom_include_in_pcb_remuneration"),
			"Shift Assignment": ("custom_roster_selection", "custom_assigned_start_datetime", "custom_shift_work_record"),
			"Employee Checkin": ("custom_roster_selection", "custom_shift_work_record", "custom_checkin_method"),
			"Salary Slip": ("custom_malaysia_statutory_results", "custom_malaysia_statutory_snapshot"),
			"Payroll Entry": ("custom_malaysia_payroll_run",),
		}
		for doctype, fields in required_fields.items():
			meta = frappe.get_meta(doctype)
			for fieldname in fields:
				self.assertTrue(meta.has_field(fieldname), f"{doctype}.{fieldname}")

	def test_managed_roles_components_and_print_formats_exist(self):
		for role in ROLES:
			self.assertTrue(frappe.db.exists("Role", role), role)
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

	def test_legacy_epf_export_is_disabled_by_default(self):
		settings = frappe.get_cached_doc("Malaysia Workforce Settings")
		self.assertEqual(int(settings.enable_legacy_epf_ecaruman_csv_for_uat or 0), 0)

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
			mw_hooks.add_to_apps_screen,
		):
			targets.update(item for item in flatten(source) if item.startswith("malaysia_workforce."))

		for target in sorted(targets):
			self.assertTrue(callable(frappe.get_attr(target)), target)
