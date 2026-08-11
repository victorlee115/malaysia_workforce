from __future__ import annotations

import frappe
from frappe.tests import IntegrationTestCase

from malaysia_workforce.api.attendance import kiosk_clock
from malaysia_workforce.compliance.activation import activate_company
from malaysia_workforce.compliance.approvals import prevent_self_approval
from malaysia_workforce.compliance.exceptions import create_assigned_exception
from malaysia_workforce.compliance.incidents import annual_incident_register, record_workplace_incident
from malaysia_workforce.compliance.scope import validate_payroll_entry_scope, validate_work_agreement_scope
from malaysia_workforce.live_tests.scenarios import (
	EMPLOYEE_EMAIL,
	KIOSK_CREDENTIAL,
	KIOSK_ID,
	exercise_payroll_uat,
	seed_demo,
)


class TestOperationalScenarios(IntegrationTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def test_cafe_operational_control_matrix(self):
		result = seed_demo()
		self.assertEqual(result["published"]["status"], "Approved")
		self.assertTrue(frappe.db.exists("Shift Assignment", result["shift_assignment"]))
		self.assertTrue(frappe.db.exists("Attendance", result["attendance"]))
		self.assertFalse(frappe.db.exists("DocType", "Casual Roster"))
		self.assertIn(result["work_record_status"], {"Automatically Verified", "Payroll Generated"})
		self.assertEqual(result["work_record_docstatus"], 1)
		self.assertGreater(float(result["gross_pay"]), 0)
		self.assertEqual(len(set(result["checkins"])), 2)
		self.assertTrue(result["duplicate"]["duplicate"])
		payroll = exercise_payroll_uat()
		self.assertTrue(payroll["salary_slips"])
		self.assertEqual(payroll["bank"]["employee_count"], 1)
		self.assertTrue(payroll["bank"].get("uat_only") or payroll["bank"].get("idempotent_replay"))
		self.assertTrue(payroll["release_blocked_without_activation"])

		with self.assertRaises(frappe.PermissionError):
			kiosk_clock(
				event_id="MW-E2E-BAD-SIGNATURE",
				kiosk_id=KIOSK_ID,
				employee=result["employee"],
				credential=KIOSK_CREDENTIAL,
				log_type="IN",
				device_timestamp=str(result["shift_end"]),
				signature="0" * 64,
			)

		with self.assertRaises(frappe.ValidationError):
			validate_work_agreement_scope(
				frappe._dict(
					company=result["company"],
					jurisdiction="Sabah",
					contract_relationship="Contract of Service",
					work_arrangement="Casual",
				)
			)

		expired_entry = frappe._dict(
			company=result["company"],
			end_date="2027-01-31",
			custom_malaysia_final_run=1,
			employees=[],
		)
		with self.assertRaises(frappe.ValidationError):
			validate_payroll_entry_scope(expired_entry)

		with self.assertRaises(frappe.ValidationError):
			activate_company(result["company"])

		incident = record_workplace_incident(
			company=result["company"],
			subject="MW E2E hot-water burn",
			description="Simulated cafe workplace incident.",
			occurred_on=str(result["shift_end"]),
			employee=result["employee"],
			dosh_reporting_required=1,
		)
		self.assertEqual(len(incident["assigned_todos"]), 2)
		self.assertTrue(
			any(row.name == incident["issue"] for row in annual_incident_register(result["company"], 2026))
		)

		todo = create_assigned_exception(
			code="MW-E2E-IDEMPOTENCY",
			description="Simulated retry-safe exception.",
			reference_type="Employee",
			reference_name=result["employee"],
		)
		self.assertEqual(
			todo,
			create_assigned_exception(
				code="MW-E2E-IDEMPOTENCY",
				description="Simulated retry-safe exception.",
				reference_type="Employee",
				reference_name=result["employee"],
			),
		)

		frappe.set_user(result["hr_manager_user"])
		self.assertTrue(
			frappe.has_permission(
				"Malaysia Employee Profile", "read", doc=result["employee"]
			)
		)
		self.assertTrue(
			frappe.has_permission(
				"Cafe Staffing Plan", "read", doc=frappe.get_doc("Cafe Staffing Plan", result["staffing_plan"])
			)
		)

		frappe.set_user(result["payroll_user"])
		self.assertTrue(
			frappe.has_permission(
				"Shift Work Record", "read", doc=frappe.get_doc("Shift Work Record", result["work_record"])
			)
		)
		self.assertTrue(frappe.has_permission("Payroll Entry", "submit"))

		frappe.set_user(result["releaser_user"])
		self.assertTrue(frappe.has_permission("Payroll Entry", "read"))
		self.assertFalse(frappe.has_permission("Payroll Entry", "submit"))

		frappe.set_user(result["auditor_user"])
		profile = frappe.get_doc("Malaysia Employee Profile", result["employee"])
		plan = frappe.get_doc("Cafe Staffing Plan", result["staffing_plan"])
		self.assertTrue(frappe.has_permission("Malaysia Employee Profile", "read", doc=profile))
		self.assertFalse(frappe.has_permission("Malaysia Employee Profile", "write", doc=profile))
		self.assertTrue(frappe.has_permission("Cafe Staffing Plan", "read", doc=plan))
		self.assertFalse(frappe.has_permission("Cafe Staffing Plan", "write", doc=plan))
		self.assertTrue(frappe.has_permission("Payroll Entry", "read"))
		self.assertFalse(frappe.has_permission("Payroll Entry", "submit"))

		frappe.set_user(EMPLOYEE_EMAIL)
		with self.assertRaises(frappe.PermissionError):
			prevent_self_approval(frappe._dict(employee=result["employee"], status="Approved"))
