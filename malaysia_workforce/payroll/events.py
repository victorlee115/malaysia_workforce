from __future__ import annotations

import frappe
from frappe import _

from malaysia_workforce.utils import select_for_update


def validate_payroll_readiness(doc, method=None):
	"""Fail closed when a Malaysia-enabled Payroll Entry was not prepared."""
	if not getattr(doc, "custom_malaysia_enabled", 0) or doc.docstatus != 1:
		return
	if getattr(doc, "custom_malaysia_control_state", None) not in {
		"Validated",
		"Payroll Generated",
	}:
		frappe.throw(_("Prepare and validate Malaysia inputs before submitting this Payroll Entry."))
	if not getattr(doc, "custom_malaysia_source_snapshot_hash", None):
		frappe.throw(_("The Malaysia payroll source snapshot is missing. Prepare the Payroll Entry again."))


def on_payroll_entry_submit(doc, method=None):
	if not getattr(doc, "custom_malaysia_enabled", 0):
		return
	frappe.db.set_value(
		"Payroll Entry",
		doc.name,
		{
			"custom_malaysia_control_state": "Payroll Generated",
			"custom_malaysia_work_record_reservation_status": "Reserved",
		},
		update_modified=True,
	)


def maybe_finalize_payroll_entry_after_salary_slip_submit(doc) -> bool:
	"""Move a standard Payroll Entry to human release after every slip is submitted."""
	payroll_entry = getattr(doc, "payroll_entry", None)
	if not payroll_entry or frappe.db.get_value("Payroll Entry", payroll_entry, "docstatus") != 1:
		return False
	if not frappe.db.get_value("Payroll Entry", payroll_entry, "custom_malaysia_enabled"):
		return False

	expected = frappe.db.count("Payroll Employee Detail", {"parent": payroll_entry, "parenttype": "Payroll Entry"})
	if not expected:
		return False
	submitted = frappe.db.count("Salary Slip", {"payroll_entry": payroll_entry, "docstatus": 1})
	draft = frappe.db.count("Salary Slip", {"payroll_entry": payroll_entry, "docstatus": 0})
	if submitted != expected or draft:
		return False

	select_for_update("SELECT name FROM `tabPayroll Entry` WHERE name=%s", (payroll_entry,))
	entry = frappe.get_doc("Payroll Entry", payroll_entry)
	settings = frappe.get_cached_doc("Malaysia Workforce Settings")
	if settings.auto_create_employer_contribution_journal:
		from malaysia_workforce.payroll.services import create_employer_contribution_journal

		create_employer_contribution_journal(payroll_entry=entry)

	from malaysia_workforce.compliance.scope import payroll_source_hash

	frappe.db.set_value(
		"Payroll Entry",
		payroll_entry,
		{
			"custom_malaysia_source_snapshot_hash": payroll_source_hash(payroll_entry),
			"custom_malaysia_control_state": "Awaiting Human Release",
		},
		update_modified=True,
	)
	if settings.auto_generate_statutory_files_on_final_run and entry.custom_malaysia_final_run:
		frappe.enqueue(
			"malaysia_workforce.payroll.jobs.generate_statutory_files_for_payroll_entry",
			queue="long",
			enqueue_after_commit=True,
			deduplicate=True,
			job_id=f"mw-statutory-files:{payroll_entry}",
			payroll_entry=payroll_entry,
		)
	return True


def before_payroll_entry_cancel(doc, method=None):
	"""Preserve authority evidence and invalidate only files never submitted."""
	if getattr(doc, "custom_malaysia_enabled", 0) and doc.custom_malaysia_control_state == "Released":
		frappe.throw(_("A human-released Payroll Entry cannot be cancelled; create a controlled adjustment."))
	frozen = frappe.get_all(
		"Statutory Submission",
		filters={"payroll_entry": doc.name, "status": ["in", ["Submitted", "Accepted", "Rejected", "Paid", "Reconciled"]]},
		pluck="name",
		limit=1000,
	)
	if frozen:
		frappe.throw(
			_("Payroll cannot be cancelled because authority evidence exists: {0}. Create a controlled adjustment.").format(
				", ".join(frozen[:20])
			)
		)
	for name in frappe.get_all(
		"Statutory Submission",
		filters={"payroll_entry": doc.name, "status": ["in", ["Generated", "Ready for Portal", "Not Required"]]},
		pluck="name",
		limit=1000,
	):
		submission = frappe.get_doc("Statutory Submission", name)
		if submission.generated_file:
			for file_name in frappe.get_all(
				"File",
				filters={"attached_to_doctype": "Statutory Submission", "attached_to_name": name, "attached_to_field": "generated_file"},
				pluck="name",
			):
				frappe.delete_doc("File", file_name, ignore_permissions=True, force=True)
		submission.generated_file = None
		submission.file_sha256 = None
		submission.status = "Validation Failed"
		submission.validation_errors = '["Linked payroll was cancelled before authority submission."]'
		submission.save(ignore_permissions=True)


def on_payroll_entry_cancel(doc, method=None):
	from malaysia_workforce.payroll.services import cancel_employer_contribution_journal

	cancel_employer_contribution_journal(payroll_entry=doc)
	if getattr(doc, "custom_malaysia_enabled", 0):
		frappe.db.set_value(
			"Payroll Entry",
			doc.name,
			{"custom_malaysia_control_state": "Cancelled", "custom_malaysia_final_period_key": None},
			update_modified=True,
		)


def on_additional_salary_cancel(doc, method=None):
	if not getattr(doc, "custom_generated_by_malaysia_workforce", None) or doc.ref_doctype != "Payroll Entry":
		return
	for name in frappe.get_all(
		"Shift Work Record",
		filters={"additional_salary_references": ["like", f"%{doc.name}%"]},
		pluck="name",
	):
		record = frappe.get_doc("Shift Work Record", name)
		references = [item for item in (record.additional_salary_references or "").splitlines() if item and item != doc.name]
		updates = {"additional_salary_references": "\n".join(references)}
		if not references:
			updates.update(
				{
					"status": record.pre_payroll_status or "Approved",
					"pre_payroll_status": "",
					"payroll_entry": "",
					"payroll_date": None,
				}
			)
		record.db_set(updates, update_modified=True)
