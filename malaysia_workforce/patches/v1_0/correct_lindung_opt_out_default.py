from __future__ import annotations

import frappe


def _has_column(doctype: str, fieldname: str) -> bool:
	return frappe.db.has_column(doctype, fieldname)


def execute():
	"""Treat an unrecorded LINDUNG 24 Jam employee as participating.

	PERKESO confirmed on 10 July 2026 that release from LINDUNG 24 Jam is an
	opt-out exercised by the employee. The previous release modelled it as an
	opt-in election and backfilled every employee to 'Not Set', which blocked
	payroll for the answer the law already presumes. 'Not Set' therefore means
	'Participating'.

	A recorded 'Not Participating' is left untouched: only the employee can
	release the liability, so the app must never re-enrol anyone on their
	behalf. Those rows are logged instead, because this app cannot tell a
	genuine portal Liability Release Notice from an old-model election and a
	human must re-verify each one.
	"""
	if not _has_column("Employee", "custom_lindung_participation"):
		return

	frappe.db.sql(
		"""update `tabEmployee` set custom_lindung_participation='Participating'
		where ifnull(custom_lindung_participation, '') in ('', 'Not Set')"""
	)

	# Election paperwork captured under the opt-in model is not a release
	# notice. The fields are hidden for a participating employee, so a later
	# flip to 'Not Participating' would otherwise surface a stale attachment as
	# if it were the notice. Clearing the field keeps the File itself on the
	# Employee's attachment sidebar.
	for fieldname in ("custom_lindung_effective_from", "custom_lindung_evidence"):
		if _has_column("Employee", fieldname):
			frappe.db.sql(
				f"""update `tabEmployee` set {fieldname}=null
				where custom_lindung_participation='Participating'
				and ifnull({fieldname}, '')!=''"""
			)

	unverified = frappe.db.sql_list(
		"""select name from `tabEmployee`
		where custom_lindung_participation='Not Participating' order by name"""
	)
	if unverified:
		frappe.log_error(
			message=(
				"These employees are recorded as released from LINDUNG 24 Jam under the "
				"previous opt-in model. Re-verify each against an actual PERKESO Liability "
				"Release Notice before the next payroll; an employee who never filed one "
				"is still participating.\n\n" + "\n".join(unverified)
			),
			title="LINDUNG 24 Jam releases need re-verification",
		)

	frappe.clear_cache()
