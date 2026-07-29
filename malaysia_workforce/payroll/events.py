from __future__ import annotations

import frappe
from frappe import _


def validate_payroll_readiness(doc, method=None):
	if not getattr(doc, "custom_malaysia_payroll_run", None):
		return
	run = frappe.get_doc("Malaysia Payroll Run", doc.custom_malaysia_payroll_run)
	if run.status == "Validation Failed":
		frappe.throw(_("The linked Malaysia Payroll Run has unresolved validation errors."))
	if run.company != doc.company or run.start_date != doc.start_date or run.end_date != doc.end_date:
		frappe.throw(_("Payroll Entry dates or company do not match the linked Malaysia Payroll Run."))


def on_payroll_entry_submit(doc, method=None):
	run_name = getattr(doc, "custom_malaysia_payroll_run", None)
	if not run_name:
		return
	# Frappe HR submits Payroll Entry before users submit its Salary Slips. The run
	# is complete only after every linked Salary Slip is submitted.
	frappe.db.set_value("Malaysia Payroll Run", run_name, "status", "Payroll Generated", update_modified=True)


def maybe_finalize_run_after_salary_slip_submit(doc) -> bool:
	"""Finalize the Malaysia run only when every Payroll Entry employee has a submitted slip."""
	run_name = getattr(doc, "custom_malaysia_payroll_run", None)
	payroll_entry = getattr(doc, "payroll_entry", None)
	if not run_name or not payroll_entry:
		return False
	if frappe.db.get_value("Payroll Entry", payroll_entry, "docstatus") != 1:
		return False

	expected = frappe.db.count("Payroll Employee Detail", {"parent": payroll_entry, "parenttype": "Payroll Entry"})
	if not expected:
		return False
	submitted = frappe.db.count("Salary Slip", {"payroll_entry": payroll_entry, "docstatus": 1})
	draft = frappe.db.count("Salary Slip", {"payroll_entry": payroll_entry, "docstatus": 0})
	if submitted != expected or draft:
		return False

	# Serialize concurrent final-slip submissions. All following actions are idempotent.
	frappe.db.sql("SELECT name FROM `tabMalaysia Payroll Run` WHERE name=%s FOR UPDATE", (run_name,))
	run = frappe.get_doc("Malaysia Payroll Run", run_name)
	settings = frappe.get_cached_doc("Malaysia Workforce Settings")
	if settings.auto_create_employer_contribution_journal:
		from malaysia_workforce.payroll.services import create_employer_contribution_journal

		create_employer_contribution_journal(run)
	frappe.db.set_value("Malaysia Payroll Run", run_name, "status", "Submitted", update_modified=True)
	if settings.auto_generate_statutory_files_on_final_run and run.is_final_run_for_month:
		frappe.enqueue(
			"malaysia_workforce.payroll.jobs.generate_statutory_files_for_run",
			queue="long",
			enqueue_after_commit=True,
			deduplicate=True,
			job_id=f"mw-statutory-files:{run_name}",
			run_name=run_name,
		)
	return True



def before_payroll_entry_cancel(doc, method=None):
	"""Preserve authority evidence and invalidate only files that were never submitted."""
	run_name = getattr(doc, "custom_malaysia_payroll_run", None)
	if not run_name:
		return
	frozen = frappe.get_all(
		"Statutory Submission",
		filters={
			"payroll_run": run_name,
			"status": ["in", ["Submitted", "Accepted", "Rejected", "Paid", "Reconciled"]],
		},
		pluck="name",
		limit_page_length=1000,
	)
	if frozen:
		frappe.throw(
			_("Payroll cannot be cancelled because authority submission evidence exists: {0}. Create a controlled payroll adjustment instead.").format(
				", ".join(frozen[:20])
			)
		)
	for name in frappe.get_all(
		"Statutory Submission",
		filters={"payroll_run": run_name, "status": ["in", ["Generated", "Ready for Portal", "Not Required"]]},
		pluck="name",
		limit_page_length=1000,
	):
		submission = frappe.get_doc("Statutory Submission", name)
		if submission.generated_file:
			for file_name in frappe.get_all(
				"File",
				filters={
					"attached_to_doctype": "Statutory Submission",
					"attached_to_name": submission.name,
					"attached_to_field": "generated_file",
				},
				pluck="name",
			):
				frappe.delete_doc("File", file_name, ignore_permissions=True, force=True)
		submission.generated_file = None
		submission.file_sha256 = None
		submission.status = "Validation Failed"
		submission.validation_errors = '["Linked payroll was cancelled before authority submission."]'
		submission.save(ignore_permissions=True)

def on_payroll_entry_cancel(doc, method=None):
	run_name = getattr(doc, "custom_malaysia_payroll_run", None)
	if not run_name:
		return
	from malaysia_workforce.payroll.services import cancel_employer_contribution_journal

	cancel_employer_contribution_journal(run_name)
	frappe.db.set_value("Malaysia Payroll Run", run_name, "status", "Payroll Generated", update_modified=True)


def on_additional_salary_cancel(doc, method=None):
	if not getattr(doc, "custom_generated_by_malaysia_workforce", None) or doc.ref_doctype != "Malaysia Payroll Run":
		return
	for name in frappe.get_all("Shift Work Record", filters={"additional_salary_references": ["like", f"%{doc.name}%"]}, pluck="name"):
		record = frappe.get_doc("Shift Work Record", name)
		references = [item for item in (record.additional_salary_references or "").splitlines() if item and item != doc.name]
		record.db_set("additional_salary_references", "\n".join(references), update_modified=False)
		if not references:
			record.db_set(
				{
					"status": record.pre_payroll_status or "Approved",
					"pre_payroll_status": "",
					"payroll_run": "",
					"payroll_date": None,
				},
				update_modified=True,
			)
