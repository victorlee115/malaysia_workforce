from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_months, getdate

from malaysia_workforce.compliance.exceptions import create_assigned_exception
from malaysia_workforce.forms.service import generate_annual_statements
from malaysia_workforce.statutory.submission_service import generate_submission_file, populate_submission_lines
from malaysia_workforce.utils import ensure_roles


def _ensure_permission() -> None:
	ensure_roles(
		"Statutory Administrator",
		"Malaysia Payroll User",
		"HR Manager",
		"Malaysia HR Manager",
		"System Manager",
	)


def _company(company: str):
	_company_doc = frappe.get_doc("Company", company)
	_company_doc.check_permission("read")
	return _company_doc


def _submission_filter(company: str, authority: str, submission_type: str, year: int, month: int | None, revision: int):
	filters = {
		"company": company,
		"authority": authority,
		"submission_type": submission_type,
		"contribution_year": int(year),
		"revision": int(revision),
	}
	filters["contribution_month"] = int(month) if month else ["is", "not set"]
	return filters


@frappe.whitelist(methods=["POST"])
def create_monthly_submissions(
	company: str,
	year: int,
	month: int,
	payroll_entry: str | None = None,
	revision: int = 0,
):
	_ensure_permission()
	_company(company)
	if not 1 <= int(month) <= 12:
		frappe.throw(_("Month must be between 1 and 12."))
	if payroll_entry:
		entry = frappe.get_doc("Payroll Entry", payroll_entry)
		entry.check_permission("read")
		if entry.company != company:
			frappe.throw(_("Payroll Entry belongs to another Company."))
	created = []
	for authority, submission_type in (
		("LHDN", "Monthly PCB"),
		("EPF", "EPF Form A"),
		("PERKESO", "SOCSO EIS Combined"),
		("HRD Corp", "HRD Levy"),
	):
		existing = frappe.db.get_value(
			"Statutory Submission",
			_submission_filter(company, authority, submission_type, int(year), int(month), int(revision)),
			"name",
		)
		doc = frappe.get_doc("Statutory Submission", existing) if existing else frappe.new_doc("Statutory Submission")
		if not existing:
			doc.company = company
			doc.authority = authority
			doc.submission_type = submission_type
			doc.contribution_year = int(year)
			doc.contribution_month = int(month)
			doc.revision = int(revision)
			doc.payroll_entry = payroll_entry
			doc.submission_mode = "Portal Only" if authority in {"EPF", "HRD Corp"} else "File Upload"
			doc.insert()
		elif doc.status in {"Submitted", "Accepted", "Paid", "Reconciled"}:
			frappe.throw(
				_("Submission {0} is already frozen. Create the next revision.").format(doc.name)
			)
		else:
			if payroll_entry and doc.payroll_entry and doc.payroll_entry != payroll_entry:
				frappe.throw(
					_("Submission {0} is already owned by Payroll Entry {1}.").format(
						doc.name, doc.payroll_entry
					)
				)
			changed = False
			if payroll_entry and not doc.payroll_entry:
				doc.payroll_entry = payroll_entry
				changed = True
			if changed:
				doc.save()
		populate_submission_lines(doc)
		if submission_type == "HRD Levy":
			doc.payment_due_date = getdate(add_months(f"{int(year):04d}-{int(month):02d}-01", 1)).replace(day=15)
			doc.save()
			create_assigned_exception(
				code=f"HRDCORP-LEVY-PAYMENT-{int(year):04d}{int(month):02d}",
				description=f"Review, release and pay HRD Corp levy submission {doc.name} by {doc.payment_due_date}.",
				reference_type="Statutory Submission",
				reference_name=doc.name,
				due_date=doc.payment_due_date,
			)
		created.append(doc.name)
	return created


@frappe.whitelist(methods=["POST"])
def create_next_revision(submission: str):
	_ensure_permission()
	source = frappe.get_doc("Statutory Submission", submission)
	source.check_permission("read")
	next_revision = int(source.revision or 0) + 1
	existing = frappe.db.get_value(
		"Statutory Submission",
		_submission_filter(
			source.company,
			source.authority,
			source.submission_type,
			int(source.contribution_year),
			int(source.contribution_month) if source.contribution_month else None,
			next_revision,
		),
		"name",
	)
	if existing:
		return existing
	doc = frappe.new_doc("Statutory Submission")
	for fieldname in (
		"company",
		"authority",
		"submission_type",
		"contribution_year",
		"contribution_month",
		"submission_mode",
		"payroll_entry",
	):
		doc.set(fieldname, source.get(fieldname))
	doc.revision = next_revision
	doc.status = "Draft"
	doc.insert()
	return doc.name


@frappe.whitelist(methods=["POST"])
def generate_file(submission: str):
	_ensure_permission()
	doc = frappe.get_doc("Statutory Submission", submission)
	doc.check_permission("write")
	return generate_submission_file(doc)


@frappe.whitelist(methods=["POST"])
def mark_submitted(submission: str, external_reference: str, acknowledgement: str | None = None):
	_ensure_permission()
	doc = frappe.get_doc("Statutory Submission", submission)
	return doc.mark_submitted(external_reference=external_reference, acknowledgement=acknowledgement)


@frappe.whitelist(methods=["POST"])
def mark_accepted(submission: str, acknowledgement: str | None = None):
	_ensure_permission()
	return frappe.get_doc("Statutory Submission", submission).mark_accepted(acknowledgement=acknowledgement)


@frappe.whitelist(methods=["POST"])
def mark_rejected(submission: str, reason: str):
	_ensure_permission()
	return frappe.get_doc("Statutory Submission", submission).mark_rejected(reason=reason)


@frappe.whitelist(methods=["POST"])
def mark_paid(submission: str, payment_reference: str, paid_amount, receipt: str | None = None):
	_ensure_permission()
	return frappe.get_doc("Statutory Submission", submission).mark_paid(
		payment_reference=payment_reference,
		paid_amount=paid_amount,
		receipt=receipt,
	)


@frappe.whitelist(methods=["POST"])
def reconcile(submission: str):
	_ensure_permission()
	return frappe.get_doc("Statutory Submission", submission).reconcile()


@frappe.whitelist(methods=["POST"])
def generate_year_end(company: str, tax_year: int, revision: int = 0):
	_ensure_permission()
	_company(company)
	statements = generate_annual_statements(company, int(tax_year))
	submissions = []
	for submission_type in ("CP8D Preparation", "Form E Preparation"):
		name = frappe.db.get_value(
			"Statutory Submission",
			_submission_filter(company, "LHDN", submission_type, int(tax_year), None, int(revision)),
			"name",
		)
		doc = frappe.get_doc("Statutory Submission", name) if name else frappe.new_doc("Statutory Submission")
		if not name:
			doc.company = company
			doc.authority = "LHDN"
			doc.submission_type = submission_type
			doc.contribution_year = int(tax_year)
			doc.revision = int(revision)
			doc.submission_mode = "Document Only"
			doc.insert()
		elif doc.status in {"Submitted", "Accepted", "Paid", "Reconciled"}:
			frappe.throw(_("Year-end preparation {0} is frozen. Create the next revision.").format(doc.name))
		generate_submission_file(doc)
		submissions.append(doc.name)
	return {"annual_statements": statements, "submissions": submissions}
