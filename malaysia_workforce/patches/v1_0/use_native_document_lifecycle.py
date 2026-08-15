from __future__ import annotations

import frappe
from frappe import _

from malaysia_workforce.setup.workflows import ensure_tax_declaration_workflows


def _has_column(doctype: str, fieldname: str) -> bool:
	return frappe.db.has_column(doctype, fieldname)


def _copy_company_tax_ids() -> None:
	if not _has_column("Company", "custom_lhdn_employer_tin"):
		return
	for row in frappe.db.sql(
		"select name, tax_id, custom_lhdn_employer_tin from `tabCompany` where ifnull(custom_lhdn_employer_tin, '') != ''",
		as_dict=True,
	):
		if row.tax_id and row.tax_id != row.custom_lhdn_employer_tin:
			frappe.throw(
				_("Company {0} has conflicting Tax ID and LHDN Employer TIN values. Resolve them before migration.").format(
					row.name
				)
			)
		if not row.tax_id:
			frappe.db.set_value("Company", row.name, "tax_id", row.custom_lhdn_employer_tin, update_modified=False)


def _migrate_declaration(doctype: str) -> None:
	if not _has_column(doctype, "status"):
		return
	ensure_tax_declaration_workflows()
	mapping = {
		"Draft": (0, "Draft"),
		"Submitted by Employee": (0, "Pending Review"),
		"Accepted by Employer": (1, "Approved"),
		"Superseded": (2, "Approved"),
	}
	for old_status, (docstatus, workflow_state) in mapping.items():
		frappe.db.sql(
			f"update `tab{doctype}` set docstatus=%s, workflow_state=%s where status=%s",
			(docstatus, workflow_state, old_status),
		)


def _migrate_cp38() -> None:
	if not _has_column("Malaysia CP38 Directive", "status"):
		return
	for old_status, docstatus in {"Draft": 0, "Active": 1, "Completed": 1, "Cancelled": 2}.items():
		frappe.db.sql(
			"update `tabMalaysia CP38 Directive` set docstatus=%s where status=%s",
			(docstatus, old_status),
		)


def _migrate_filings() -> None:
	if not _has_column("Malaysia Statutory Filing", "status"):
		return
	mapping = {
		"Draft": (0, "Pending", "Not Reconciled"),
		"Prepared": (0, "Pending", "Not Reconciled"),
		"Submitted": (1, "Pending", "Not Reconciled"),
		"Accepted": (1, "Accepted", "Not Reconciled"),
		"Rejected": (1, "Rejected", "Not Reconciled"),
		"Reconciled": (1, "Accepted", "Reconciled"),
		"Superseded": (2, "Pending", "Not Reconciled"),
	}
	for old_status, (docstatus, authority_status, reconciliation_status) in mapping.items():
		frappe.db.sql(
			"""update `tabMalaysia Statutory Filing`
			set docstatus=%s, authority_status=%s, reconciliation_status=%s where status=%s""",
			(docstatus, authority_status, reconciliation_status, old_status),
		)


def execute():
	"""Move RC records onto native docstatus without inferring employee consent."""
	_copy_company_tax_ids()
	_migrate_declaration("Malaysia Tax Declaration TP1")
	_migrate_declaration("Malaysia Previous Employment TP3")
	_migrate_cp38()
	_migrate_filings()
	if _has_column("Employee", "custom_lindung_participation"):
		frappe.db.sql(
			"""update `tabEmployee` set custom_lindung_participation='Not Set'
			where ifnull(custom_lindung_participation, '')=''"""
		)
	frappe.clear_cache()
