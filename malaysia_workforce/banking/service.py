from __future__ import annotations

import csv
import hashlib
import io
from decimal import Decimal, InvalidOperation

import frappe
from frappe import _
from frappe.utils import now_datetime

from malaysia_workforce.compliance.scope import assert_company_activation, payroll_source_hash
from malaysia_workforce.compliance.exceptions import create_assigned_exception
from malaysia_workforce.utils import ensure_private_file, ensure_roles, select_for_update


def bank_adapter_path(adapter_key: str) -> str | None:
	if adapter_key == "Generic CSV (UAT Only)":
		return None
	hooks = frappe.get_hooks("malaysia_workforce_bank_adapters") or {}
	if isinstance(hooks, dict):
		value = hooks.get(adapter_key)
		if isinstance(value, (list, tuple)):
			value = value[-1] if value else None
		return str(value) if value else None
	return None


def production_bank_adapter_available(adapter_key: str) -> bool:
	return bool(adapter_key and adapter_key not in {"Not Configured", "Generic CSV (UAT Only)"} and bank_adapter_path(adapter_key))


def _submitted_salary_slips(payroll_entry: str) -> list:
	return frappe.get_all(
		"Salary Slip",
		filters={"payroll_entry": payroll_entry, "docstatus": 1},
		fields=["name", "employee", "employee_name", "net_pay"],
		order_by="employee, name",
		limit=100000,
	)


def _assert_complete(entry, slips: list) -> None:
	if int(entry.docstatus or 0) != 1:
		frappe.throw(_("Submit the Payroll Entry before preparing a bank file."))
	expected = frappe.db.count(
		"Payroll Employee Detail",
		{"parent": entry.name, "parenttype": "Payroll Entry"},
	)
	if not expected or len(slips) != expected:
		frappe.throw(_("Every Payroll Entry employee must have one submitted Salary Slip."))


def _assert_no_blocking_release_exceptions(entry, slips: list) -> None:
	blocked = []
	failed_submissions = frappe.get_all(
		"Statutory Submission",
		filters={
			"payroll_entry": entry.name,
			"status": ["in", ["Validation Failed", "Rejected"]],
		},
		pluck="name",
		limit=1000,
	)
	blocked.extend(f"statutory submission {name}" for name in failed_submissions)
	employees = sorted({row.employee for row in slips})
	if employees:
		pending_corrections = frappe.get_all(
			"Employee Checkin",
			filters={
				"employee": ["in", employees],
				"time": ["between", [f"{entry.start_date} 00:00:00", f"{entry.end_date} 23:59:59"]],
				"custom_malaysia_correction_status": "Pending Review",
			},
			pluck="name",
			limit=1000,
		)
		blocked.extend(f"attendance correction {name}" for name in pending_corrections)
		attendance_names = frappe.get_all(
			"Attendance",
			filters={
				"employee": ["in", employees],
				"attendance_date": ["between", [entry.start_date, entry.end_date]],
			},
			pluck="name",
			limit=100000,
		)
		if attendance_names:
			reprocess = frappe.get_all(
				"ToDo",
				filters={
					"status": "Open",
					"reference_type": "Attendance",
					"reference_name": ["in", attendance_names],
					"custom_malaysia_exception_code": "ATTENDANCE-REPROCESS",
				},
				pluck="name",
				limit=1000,
			)
			blocked.extend(f"attendance reprocessing task {name}" for name in reprocess)
	direct = frappe.get_all(
		"ToDo",
		filters={
			"status": "Open",
			"reference_type": "Payroll Entry",
			"reference_name": entry.name,
			"custom_malaysia_exception_code": ["is", "set"],
		},
		pluck="name",
		limit=1000,
	)
	blocked.extend(f"payroll task {name}" for name in direct)
	if blocked:
		frappe.throw(
			_("Resolve blocking Malaysia exceptions before payroll release: {0}.").format(
				", ".join(blocked[:50])
			)
		)


def _net_pay_total(slips: list) -> Decimal:
	total = Decimal("0")
	for slip in slips:
		try:
			amount = Decimal(str(slip.net_pay or 0))
		except (InvalidOperation, TypeError, ValueError):
			frappe.throw(_("Salary Slip {0} has an invalid net pay.").format(slip.name))
		if not amount.is_finite() or amount < 0:
			frappe.throw(_("Salary Slip {0} must have a finite, non-negative net pay.").format(slip.name))
		total += amount.quantize(Decimal("0.01"))
	return total.quantize(Decimal("0.01"))


def _generic_uat_csv(entry, slips: list) -> tuple[str, bytes, Decimal]:
	stream = io.StringIO(newline="")
	writer = csv.writer(stream, lineterminator="\r\n")
	writer.writerow(["UAT ONLY - NOT A BANK UPLOAD FILE"])
	writer.writerow(["Employee ID", "Employee Name", "Bank Account", "Net Pay (MYR)"])
	total = Decimal("0")
	for slip in slips:
		bank_account = frappe.db.get_value("Employee", slip.employee, "bank_ac_no") or ""
		amount = Decimal(str(slip.net_pay or 0)).quantize(Decimal("0.01"))
		total += amount
		writer.writerow([slip.employee, slip.employee_name or "", bank_account, f"{amount:.2f}"])
	writer.writerow(["CONTROL TOTAL", len(slips), "", f"{total:.2f}"])
	filename = f"malaysia-payroll-{entry.name}-UAT.csv"
	return filename, stream.getvalue().encode("utf-8-sig"), total


def _adapter_artifact(file_format: str, entry, slips: list, expected_total: Decimal) -> tuple[str, bytes, Decimal]:
	adapter_path = bank_adapter_path(file_format)
	if not adapter_path:
		frappe.throw(_("No approved adapter is installed for bank format {0}.").format(file_format))
	result = frappe.get_attr(adapter_path)(entry=entry, salary_slips=slips)
	if not isinstance(result, dict) or not result.get("filename") or not isinstance(result.get("content"), bytes):
		frappe.throw(_("Bank adapter {0} returned an invalid artifact contract.").format(file_format))
	try:
		total = Decimal(str(result.get("control_total"))).quantize(Decimal("0.01"))
	except (InvalidOperation, TypeError, ValueError):
		frappe.throw(_("Bank adapter {0} returned an invalid control total.").format(file_format))
	if not total.is_finite() or total != expected_total:
		frappe.throw(
			_("Bank adapter {0} control total {1} does not match Payroll Entry net pay {2}.").format(
				file_format, total, expected_total
			)
		)
	return result["filename"], result["content"], total


def _save_private_file(entry, filename: str, content: bytes) -> str:
	for name in frappe.get_all(
		"File",
		filters={
			"attached_to_doctype": "Payroll Entry",
			"attached_to_name": entry.name,
			"attached_to_field": "custom_malaysia_bank_file",
		},
		pluck="name",
	):
		frappe.delete_doc("File", name, ignore_permissions=True, force=True)
	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": filename,
			"content": content,
			"is_private": 1,
			"attached_to_doctype": "Payroll Entry",
			"attached_to_name": entry.name,
			"attached_to_field": "custom_malaysia_bank_file",
		}
	)
	file_doc.save(ignore_permissions=True)
	return file_doc.file_url


def _stored_private_file(entry) -> bytes:
	file_name = frappe.db.get_value(
		"File",
		{
			"file_url": entry.custom_malaysia_bank_file,
			"attached_to_doctype": "Payroll Entry",
			"attached_to_name": entry.name,
			"attached_to_field": "custom_malaysia_bank_file",
			"is_private": 1,
		},
		"name",
	)
	if not file_name:
		frappe.throw(_("The private bank artifact is missing from this Payroll Entry."))
	content = frappe.get_doc("File", file_name).get_content()
	return content.encode() if isinstance(content, str) else content


@frappe.whitelist(methods=["POST"])
def prepare_bank_file(payroll_entry: str) -> dict:
	ensure_roles("Malaysia Payroll User", "System Manager")
	select_for_update("SELECT name FROM `tabPayroll Entry` WHERE name=%s", (payroll_entry,))
	entry = frappe.get_doc("Payroll Entry", payroll_entry)
	entry.check_permission("read")
	if not entry.custom_malaysia_enabled:
		frappe.throw(_("Malaysia controls are not enabled on this Payroll Entry."))
	slips = _submitted_salary_slips(entry.name)
	_assert_complete(entry, slips)
	current_source_hash = payroll_source_hash(entry.name)
	control_total = _net_pay_total(slips)
	if entry.custom_malaysia_bank_file:
		if entry.custom_malaysia_source_snapshot_hash != current_source_hash:
			frappe.throw(_("Payroll sources changed after bank-file preparation. Cancel or revalidate the payroll; the prior artifact will not be overwritten."))
		return {
			"file_url": entry.custom_malaysia_bank_file,
			"sha256": entry.custom_malaysia_bank_file_hash,
			"employee_count": len(slips),
			"control_total": str(control_total),
			"idempotent_replay": True,
		}
	file_format, production = frappe.db.get_value(
		"Company",
		entry.company,
		["custom_malaysia_bank_file_format", "custom_malaysia_production_activated"],
	)
	if file_format in {None, "", "Not Configured"}:
		frappe.throw(_("Configure and UAT a bank payroll file format before generating a file."))
	if file_format == "Generic CSV (UAT Only)":
		if production:
			frappe.throw(_("The generic CSV is UAT-only and cannot be generated for an activated production Company."))
		filename, content, total = _generic_uat_csv(entry, slips)
	else:
		filename, content, total = _adapter_artifact(file_format, entry, slips, control_total)
	file_url = _save_private_file(entry, filename, content)
	digest = hashlib.sha256(content).hexdigest()
	frappe.db.set_value(
		"Payroll Entry",
		entry.name,
		{
			"custom_malaysia_bank_file": file_url,
			"custom_malaysia_bank_file_hash": digest,
			"custom_malaysia_bank_reconciliation_state": "Prepared",
			"custom_malaysia_source_snapshot_hash": current_source_hash,
			"custom_malaysia_control_state": "Awaiting Human Release",
			"custom_malaysia_processed_by": entry.custom_malaysia_processed_by or frappe.session.user,
		},
		update_modified=True,
	)
	return {
		"file_url": file_url,
		"sha256": digest,
		"employee_count": len(slips),
		"control_total": str(total),
		"uat_only": file_format == "Generic CSV (UAT Only)",
	}


@frappe.whitelist(methods=["POST"])
def reconcile_bank_file(
	payroll_entry: str,
	bank_reference: str,
	paid_employee_count: int,
	paid_total,
	evidence: str,
) -> dict:
	ensure_roles("HR Manager", "Malaysia HR Manager", "System Manager")
	select_for_update("SELECT name FROM `tabPayroll Entry` WHERE name=%s", (payroll_entry,))
	entry = frappe.get_doc("Payroll Entry", payroll_entry)
	entry.check_permission("read")
	if entry.custom_malaysia_control_state != "Released":
		frappe.throw(_("Release the Payroll Entry before bank reconciliation."))
	if not bank_reference or not evidence:
		frappe.throw(_("Bank batch reference and reconciliation evidence are required."))
	evidence = ensure_private_file(evidence, _("Bank reconciliation evidence"))
	slips = _submitted_salary_slips(entry.name)
	_assert_complete(entry, slips)
	expected_total = _net_pay_total(slips)
	try:
		actual_total = Decimal(str(paid_total)).quantize(Decimal("0.01"))
	except (InvalidOperation, TypeError, ValueError):
		frappe.throw(_("Paid total must be a valid amount."))
	if not actual_total.is_finite() or actual_total < 0:
		frappe.throw(_("Paid total must be finite and non-negative."))
	difference = actual_total - expected_total
	if int(paid_employee_count) != len(slips) or abs(difference) > Decimal("0.01"):
		frappe.db.set_value(
			"Payroll Entry",
			entry.name,
			{
				"custom_malaysia_bank_reconciliation_state": "Failed",
				"custom_malaysia_bank_paid_count": int(paid_employee_count),
				"custom_malaysia_bank_paid_total": actual_total,
				"custom_malaysia_bank_difference": difference,
			},
			update_modified=True,
		)
		create_assigned_exception(
			code="BANK-RECONCILIATION-MISMATCH",
			description=f"Bank result for {entry.name} does not match the employee count or net-pay total (difference {difference}).",
			reference_type="Payroll Entry",
			reference_name=entry.name,
		)
		return {
			"payroll_entry": entry.name,
			"expected_employee_count": len(slips),
			"paid_employee_count": int(paid_employee_count),
			"expected_total": str(expected_total),
			"paid_total": str(actual_total),
			"difference": str(difference),
			"state": "Failed",
		}
	frappe.db.set_value(
		"Payroll Entry",
		entry.name,
		{
			"custom_malaysia_bank_reconciliation_state": "Reconciled",
			"custom_malaysia_bank_reference": str(bank_reference).strip(),
			"custom_malaysia_bank_paid_count": len(slips),
			"custom_malaysia_bank_paid_total": actual_total,
			"custom_malaysia_bank_difference": difference,
			"custom_malaysia_bank_evidence": evidence,
		},
		update_modified=True,
	)
	return {
		"payroll_entry": entry.name,
		"employee_count": len(slips),
		"expected_total": str(expected_total),
		"paid_total": str(actual_total),
		"difference": str(difference),
		"state": "Reconciled",
	}


@frappe.whitelist(methods=["POST"])
def release_payroll(payroll_entry: str) -> dict:
	ensure_roles("HR Manager", "Malaysia HR Manager", "System Manager")
	select_for_update("SELECT name FROM `tabPayroll Entry` WHERE name=%s", (payroll_entry,))
	entry = frappe.get_doc("Payroll Entry", payroll_entry)
	entry.check_permission("read")
	assert_company_activation(entry.company)
	if entry.custom_malaysia_processed_by == frappe.session.user or entry.owner == frappe.session.user:
		frappe.throw(_("The payroll processor cannot perform the final human release. Assign this Payroll Entry to another HR Manager."))
	slips = _submitted_salary_slips(entry.name)
	_assert_complete(entry, slips)
	_assert_no_blocking_release_exceptions(entry, slips)
	if not entry.custom_malaysia_bank_file or not entry.custom_malaysia_bank_file_hash:
		frappe.throw(_("Prepare and verify the bank payroll file before human release."))
	stored_content = _stored_private_file(entry)
	if hashlib.sha256(stored_content).hexdigest() != entry.custom_malaysia_bank_file_hash:
		frappe.throw(_("The stored bank artifact no longer matches its protected SHA-256 hash."))
	current_hash = payroll_source_hash(entry.name)
	if entry.custom_malaysia_source_snapshot_hash != current_hash:
		frappe.throw(_("Salary Slip or statutory source data changed after bank-file preparation."))
	file_format = frappe.db.get_value("Company", entry.company, "custom_malaysia_bank_file_format")
	_, regenerated_content, _ = _adapter_artifact(
		file_format,
		entry,
		slips,
		_net_pay_total(slips),
	)
	if hashlib.sha256(regenerated_content).hexdigest() != entry.custom_malaysia_bank_file_hash:
		frappe.throw(_("The bank adapter output changed after preparation. Regenerate and revalidate the artifact."))
	if entry.custom_malaysia_control_state == "Released":
		return {
			"payroll_entry": entry.name,
			"released_by": entry.custom_malaysia_released_by,
			"released_on": entry.custom_malaysia_released_on,
		}
	released_on = now_datetime()
	frappe.db.set_value(
		"Payroll Entry",
		entry.name,
		{
			"custom_malaysia_control_state": "Released",
			"custom_malaysia_released_by": frappe.session.user,
			"custom_malaysia_released_on": released_on,
			"custom_malaysia_bank_reconciliation_state": "Authorised",
		},
		update_modified=True,
	)
	return {
		"payroll_entry": entry.name,
		"released_by": frappe.session.user,
		"released_on": released_on,
	}
