from __future__ import annotations

import csv
import io
import json
from collections import defaultdict
from decimal import Decimal
from typing import Any

import frappe
from frappe import _
from frappe.utils import get_last_day, getdate, now_datetime

from malaysia_workforce.data_access import get_malaysia_profile
from malaysia_workforce.compliance.scope import assert_employee_supported, assert_rule_review_current
from malaysia_workforce.statutory.exporters.common import digits
from malaysia_workforce.statutory.exporters.epf_csv import EPFCSVRecord, generate_epf_csv
from malaysia_workforce.statutory.exporters.lhdn_pcb import LHDNPCBRecord, generate_lhdn_pcb_file
from malaysia_workforce.statutory.exporters.perkeso_combined import (
	PERKESOCombinedRecord,
	generate_perkeso_combined_file,
)
from malaysia_workforce.statutory.snapshot import parse_json_object, parse_statutory_snapshot
from malaysia_workforce.utils import ensure_roles, select_for_update, sha256_bytes, stable_json

MONTHLY_TYPES = {"Monthly PCB", "EPF Form A", "SOCSO EIS Combined", "HRD Levy"}
ANNUAL_PREPARATION_TYPES = {"CP8D Preparation", "Form E Preparation"}
FROZEN_STATUSES = {"Submitted", "Accepted", "Rejected", "Paid", "Reconciled"}
SCHEMA_VERSIONS = {
	"Monthly PCB": "LHDN-MTD-TEXT-EXHIBIT-4-2026",
	"EPF Form A": "KWSP-IAKAUN-EMPLOYER-PORTAL-WORKSHEET-2026.1",
	"SOCSO EIS Combined": "PERKESO-COMBINED-278-2026",
	"HRD Levy": "HRDCORP-LEVY-PORTAL-WORKSHEET-2026.1",
	"CP8D Preparation": "MW-PREPARATION-WORKSHEET-2026.1",
	"Form E Preparation": "MW-PREPARATION-WORKSHEET-2026.1",
}


def _ensure_permission() -> None:
	ensure_roles(
		"Statutory Administrator",
		"Malaysia Payroll User",
		"HR Manager",
		"Malaysia HR Manager",
		"System Manager",
	)


def _ensure_company_access(company: str) -> None:
	if not company or not frappe.db.exists("Company", company):
		frappe.throw(_("Select a valid Company."))
	frappe.get_doc("Company", company).check_permission("read")


def _month_range(year: int, month: int):
	start = getdate(f"{int(year):04d}-{int(month):02d}-01")
	return start, getdate(get_last_day(start))


def _load_snapshot(value: str | None, context: str) -> dict[str, Any]:
	try:
		return parse_statutory_snapshot(value)
	except ValueError as exc:
		frappe.throw(_("{0} has an invalid Malaysia statutory snapshot: {1}").format(context, exc))


def _salary_slip_rows(company: str, year: int, month: int | None = None) -> list:
	if month:
		start, end = _month_range(year, month)
	else:
		start, end = getdate(f"{year}-01-01"), getdate(f"{year}-12-31")
	return frappe.get_all(
		"Salary Slip",
		filters={
			"company": company,
			"docstatus": 1,
			"end_date": ["between", [start, end]],
			"custom_malaysia_statutory_snapshot": ["is", "set"],
		},
		fields=[
			"name",
			"employee",
			"employee_name",
			"start_date",
			"end_date",
			"posting_date",
			"custom_malaysia_statutory_snapshot",
		],
		order_by="employee, end_date, name",
		limit=50000,
	)


def _monthly_employee_data(company: str, year: int, month: int) -> tuple[dict[str, dict], list[dict]]:
	rows = _salary_slip_rows(company, year, month)
	data: dict[str, dict] = {}
	source_rows: list[dict] = []
	for row in rows:
		snapshot = _load_snapshot(row.custom_malaysia_statutory_snapshot, f"Salary Slip {row.name}")
		source_rows.append(
			{
				"salary_slip": row.name,
				"employee": row.employee,
				"start_date": str(row.start_date),
				"end_date": str(row.end_date),
				"posting_date": str(row.posting_date),
				"snapshot_sha256": sha256_bytes(stable_json(snapshot).encode("utf-8")),
			}
		)
		item = data.setdefault(
			row.employee,
			{
				"employee": row.employee,
				"employee_name": row.employee_name,
				"bases": defaultdict(lambda: Decimal("0")),
				"results": defaultdict(
					lambda: {
						"employee": Decimal("0"),
						"employer": Decimal("0"),
						"extra": Decimal("0"),
						"versions": set(),
						"applicable": False,
					}
				),
				"cp38": Decimal("0"),
			},
		)
		for key, value in snapshot.get("current_wage_bases", {}).items():
			item["bases"][key] += Decimal(str(value or 0))
		item["cp38"] += Decimal(str(snapshot.get("current_cp38") or 0))
		for result in snapshot.get("current_results", []):
			scheme = result.get("scheme")
			if not scheme:
				continue
			bucket = item["results"][scheme]
			bucket["employee"] += Decimal(str(result.get("employee_amount") or 0))
			bucket["employer"] += Decimal(str(result.get("employer_amount") or 0))
			bucket["extra"] += Decimal(str(result.get("extra_employee_amount") or 0))
			bucket["applicable"] = bucket["applicable"] or bool(result.get("applicable"))
			if result.get("rule_version"):
				bucket["versions"].add(result["rule_version"])
	return data, source_rows


def _company_reference_snapshot(company) -> dict[str, str]:
	return {
		"company": company.name,
		"registration_number": company.custom_company_registration_number or "",
		"lhdn_hq_number": company.custom_lhdn_hq_number or "",
		"lhdn_employer_number": company.custom_lhdn_employer_number or "",
		"epf_employer_number": company.custom_epf_employer_number or "",
		"socso_employer_code": company.custom_socso_employer_code or "",
		"hrd_corp_registration_number": company.custom_hrd_corp_registration_number or "",
	}


def _portal_url(authority: str) -> str:
	settings = frappe.get_cached_doc("Malaysia Workforce Settings")
	return {
		"LHDN": settings.lhdn_portal_url,
		"EPF": settings.epf_portal_url,
		"PERKESO": settings.perkeso_portal_url,
		"HRD Corp": settings.hrd_corp_portal_url,
	}.get(authority, "") or ""


def _ensure_legacy_epf_uat_enabled() -> None:
	settings = frappe.get_cached_doc("Malaysia Workforce Settings")
	if not int(settings.enable_legacy_epf_ecaruman_csv_for_uat or 0):
		frappe.throw(
			_(
				"EPF CSV generation is disabled. The bundled format is based on the discontinued "
				"e-Caruman guide and has not been verified for the current i-Akaun (Employer) "
				"contribution workflow. Configure a verified EPF adapter, or explicitly enable the "
				"legacy exporter for isolated UAT only."
			),
			title=_("Unverified EPF File Format"),
		)


def _line_for_hash(row) -> dict[str, Any]:
	return {
		"employee": row.employee,
		"employee_name": row.employee_name,
		"employee_number": row.employee_number,
		"identity_number": row.identity_number,
		"old_ic_number": row.old_ic_number,
		"new_ic_number": row.new_ic_number,
		"passport_number": row.passport_number,
		"country_code": row.country_code,
		"tin": row.tin,
		"agency_number": row.agency_number,
		"wages": str(row.wages or 0),
		"employee_amount": str(row.employee_amount or 0),
		"employer_amount": str(row.employer_amount or 0),
		"extra_employee_amount": str(row.extra_employee_amount or 0),
		"mtd_amount": str(row.mtd_amount or 0),
		"cp38_amount": str(row.cp38_amount or 0),
		"rule_version": row.rule_version,
	}


def _validate_monthly_line(submission_type: str, employee: str, line: dict, item: dict) -> list[str]:
	errors: list[str] = []
	if submission_type == "Monthly PCB":
		if not line["tin"]:
			errors.append(f"{employee}: missing Income Tax Number for an LHDN line.")
		elif len(digits(line["tin"])) > 11:
			errors.append(f"{employee}: LHDN TIN exceeds 11 numeric digits after removing its prefix.")
		if not (line["new_ic_number"] or line["passport_number"] or line["old_ic_number"]):
			errors.append(f"{employee}: missing NRIC, old IC or passport for an LHDN line.")
		if line["passport_number"] and len(line["country_code"] or "") != 2:
			errors.append(f"{employee}: a two-character LHDN country code is required with a passport.")
	elif submission_type == "EPF Form A":
		if not line["agency_number"]:
			errors.append(f"{employee}: missing EPF Member Number.")
		if not line["identity_number"]:
			errors.append(f"{employee}: missing NRIC or passport for the EPF line.")
	elif submission_type == "SOCSO EIS Combined":
		if not line["identity_number"]:
			errors.append(f"{employee}: missing NRIC/passport/SSFW identifier for a PERKESO line.")
		if len(line["identity_number"] or "") > 12:
			errors.append(f"{employee}: PERKESO identification number exceeds the 12-character field.")
		socso = item["results"].get("SOCSO", {})
		eis = item["results"].get("EIS", {})
		if bool(socso.get("applicable")) and bool(eis.get("applicable")):
			socso_wage = item["bases"].get("socso", Decimal("0"))
			eis_wage = item["bases"].get("eis", Decimal("0"))
			if abs(socso_wage - eis_wage) > Decimal("0.01"):
				errors.append(
					f"{employee}: SOCSO wages ({socso_wage:.2f}) and EIS wages ({eis_wage:.2f}) differ, "
					"but the combined ASSIST file has one salary field. Correct the Salary Component classifications."
				)
	elif submission_type == "HRD Levy":
		if Decimal(str(line["employer_amount"] or 0)) <= 0:
			errors.append(f"{employee}: HRD Corp levy line must have a positive employer amount.")
	return errors


def populate_submission_lines(submission) -> list[str]:
	_ensure_permission()
	_ensure_company_access(submission.company)
	if submission.status in FROZEN_STATUSES:
		frappe.throw(_("This submission has already been submitted. Create a new revision."))
	if submission.submission_type not in MONTHLY_TYPES:
		return []
	if not submission.contribution_month:
		frappe.throw(_("Contribution Month is required."))

	data, source_rows = _monthly_employee_data(
		submission.company,
		int(submission.contribution_year),
		int(submission.contribution_month),
	)
	submission.set("employee_lines", [])
	errors: list[str] = []

	for employee, item in sorted(data.items()):
		try:
			assert_employee_supported(employee, submission.company)
		except (frappe.ValidationError, frappe.PermissionError) as exc:
			errors.append(f"{employee}: {exc}")
			continue
		profile = get_malaysia_profile(employee)
		if not profile:
			errors.append(f"{employee}: Malaysia Employee Profile is missing.")
			continue
		identity = profile.nric_number or profile.passport_number or ""
		employee_number = frappe.db.get_value("Employee", employee, "employee_number") or str(employee)[-10:]
		line = {
			"employee": employee,
			"employee_name": item["employee_name"],
			"employee_number": employee_number,
			"identity_number": identity,
			"old_ic_number": profile.old_ic_number or "",
			"new_ic_number": profile.nric_number or "",
			"passport_number": profile.passport_number or "",
			"country_code": profile.passport_country_code or "",
			"tin": profile.income_tax_number or "",
			"agency_number": "",
			"wages": Decimal("0"),
			"employee_amount": Decimal("0"),
			"employer_amount": Decimal("0"),
			"extra_employee_amount": Decimal("0"),
			"mtd_amount": Decimal("0"),
			"cp38_amount": Decimal("0"),
			"rule_version": "",
			"validation_status": "Valid",
		}

		if submission.submission_type == "Monthly PCB":
			result = item["results"].get("PCB", {})
			if Decimal(str(result.get("employee") or 0)) <= 0 and item["cp38"] <= 0:
				continue
			line["agency_number"] = line["tin"]
			line["wages"] = item["bases"].get("pcb_regular", Decimal("0")) + item["bases"].get(
				"pcb_additional", Decimal("0")
			)
			line["employee_amount"] = Decimal(str(result.get("employee") or 0))
			line["mtd_amount"] = line["employee_amount"]
			line["cp38_amount"] = item["cp38"]
			line["rule_version"] = ", ".join(sorted(result.get("versions", set())))
		elif submission.submission_type == "EPF Form A":
			result = item["results"].get("EPF", {})
			if Decimal(str(result.get("employee") or 0)) == 0 and Decimal(str(result.get("employer") or 0)) == 0:
				continue
			line["agency_number"] = profile.epf_number or ""
			line["wages"] = item["bases"].get("epf", Decimal("0"))
			line["employee_amount"] = Decimal(str(result.get("employee") or 0))
			line["employer_amount"] = Decimal(str(result.get("employer") or 0))
			line["rule_version"] = ", ".join(sorted(result.get("versions", set())))
		elif submission.submission_type == "SOCSO EIS Combined":
			socso = item["results"].get("SOCSO", {})
			eis = item["results"].get("EIS", {})
			lindung = item["results"].get("LINDUNG 24 Jam", {})
			if not any(
				Decimal(str(value or 0)) != 0
				for value in (
					socso.get("employee"),
					socso.get("employer"),
					eis.get("employee"),
					eis.get("employer"),
					lindung.get("extra"),
				)
			):
				continue
			line["agency_number"] = profile.socso_number or ""
			socso_wage = item["bases"].get("socso", Decimal("0"))
			eis_wage = item["bases"].get("eis", Decimal("0"))
			line["wages"] = socso_wage if socso_wage else eis_wage
			line["employee_amount"] = Decimal(str(socso.get("employee") or 0)) + Decimal(
				str(eis.get("employee") or 0)
			)
			line["employer_amount"] = Decimal(str(socso.get("employer") or 0)) + Decimal(
				str(eis.get("employer") or 0)
			)
			line["extra_employee_amount"] = Decimal(str(lindung.get("extra") or 0))
			line["rule_version"] = ", ".join(
				sorted(
					set(socso.get("versions", set()))
					| set(eis.get("versions", set()))
					| set(lindung.get("versions", set()))
				)
			)
		else:
			result = item["results"].get("HRD Corp", {})
			if Decimal(str(result.get("employer") or 0)) == 0:
				continue
			line["wages"] = item["bases"].get("hrd", Decimal("0"))
			line["employer_amount"] = Decimal(str(result.get("employer") or 0))
			line["rule_version"] = ", ".join(sorted(result.get("versions", set())))

		line_errors = _validate_monthly_line(submission.submission_type, employee, line, item)
		if line_errors:
			line["validation_status"] = "\n".join(line_errors)
			errors.extend(line_errors)
		submission.append("employee_lines", line)

	if submission.submission_type == "Monthly PCB":
		seen_employee_numbers: dict[str, str] = {}
		for row in submission.employee_lines:
			number = (row.employee_number or "").strip().upper()
			if not number or len(number.encode("ascii", errors="ignore")) > 10:
				message = f"{row.employee}: LHDN employee/salary number must contain 1 to 10 ASCII characters."
				row.validation_status = message
				errors.append(message)
			elif number in seen_employee_numbers:
				message = f"{row.employee}: LHDN employee/salary number duplicates {seen_employee_numbers[number]}."
				row.validation_status = message
				errors.append(message)
			else:
				seen_employee_numbers[number] = row.employee

	company = frappe.get_cached_doc("Company", submission.company)
	references = _company_reference_snapshot(company)
	submission.schema_version = SCHEMA_VERSIONS[submission.submission_type]
	submission.portal_url = _portal_url(submission.authority)
	submission.employer_reference_snapshot = json.dumps(references, sort_keys=True)
	submission.source_salary_slips = json.dumps(source_rows, sort_keys=True, indent=2)
	submission.source_snapshot_hash = sha256_bytes(
		stable_json(
			{
				"source_salary_slips": source_rows,
				"employee_lines": [_line_for_hash(row) for row in submission.employee_lines],
				"employer_references": references,
				"schema_version": submission.schema_version,
			}
		).encode("utf-8")
	)
	submission.validation_errors = json.dumps(errors, indent=2)
	submission.status = "Validation Failed" if errors else "Draft"
	submission.save()
	return errors


def _annual_rows(company: str, year: int) -> list[dict]:
	slips = _salary_slip_rows(company, year)
	data = defaultdict(
		lambda: {
			"gross": Decimal("0"),
			"epf": Decimal("0"),
			"socso": Decimal("0"),
			"eis": Decimal("0"),
			"pcb": Decimal("0"),
			"cp38": Decimal("0"),
			"zakat": Decimal("0"),
		}
	)
	names: dict[str, str] = {}
	for slip in slips:
		names[slip.employee] = slip.employee_name
		snapshot = _load_snapshot(
			slip.custom_malaysia_statutory_snapshot,
			f"Salary Slip {slip.name}",
		)
		bases = snapshot.get("current_wage_bases", {})
		data[slip.employee]["gross"] += Decimal(str(bases.get("gross") or 0))
		data[slip.employee]["cp38"] += Decimal(str(snapshot.get("current_cp38") or 0))
		data[slip.employee]["zakat"] += Decimal(str(snapshot.get("current_zakat") or 0))
		for result in snapshot.get("current_results", []):
			scheme = result.get("scheme")
			amount = Decimal(str(result.get("employee_amount") or 0)) + Decimal(
				str(result.get("extra_employee_amount") or 0)
			)
			if scheme == "EPF":
				data[slip.employee]["epf"] += amount
			elif scheme in {"SOCSO", "LINDUNG 24 Jam"}:
				data[slip.employee]["socso"] += amount
			elif scheme == "EIS":
				data[slip.employee]["eis"] += amount
			elif scheme == "PCB":
				data[slip.employee]["pcb"] += amount
	rows = []
	for employee in sorted(data):
		profile = get_malaysia_profile(employee)
		rows.append(
			{
				"employee": employee,
				"employee_name": names.get(employee),
				"identity_number": (profile.nric_number or profile.passport_number) if profile else "",
				"tin": profile.income_tax_number if profile else "",
				**data[employee],
			}
		)
	return rows


def _annual_csv(submission) -> bytes:
	rows = _annual_rows(submission.company, int(submission.contribution_year))
	stream = io.StringIO(newline="")
	writer = csv.writer(stream, lineterminator="\r\n")
	writer.writerow(
		[
			"PREPARATION WORKSHEET ONLY",
			"Not an official LHDN upload file",
			SCHEMA_VERSIONS[submission.submission_type],
		]
	)
	if submission.submission_type == "CP8D Preparation":
		writer.writerow(
			[
				"Employee",
				"Name",
				"Identity No",
				"TIN",
				"Gross Remuneration",
				"EPF Employee",
				"SOCSO/SKBBK Employee",
				"EIS Employee",
				"PCB",
				"CP38",
				"Zakat",
			]
		)
		for row in rows:
			writer.writerow(
				[
					row["employee"],
					row["employee_name"],
					row["identity_number"],
					row["tin"],
					*[f"{row[key]:.2f}" for key in ("gross", "epf", "socso", "eis", "pcb", "cp38", "zakat")],
				]
			)
	else:
		writer.writerow(["Form E Preparation", submission.contribution_year])
		writer.writerow(["Employee count", len(rows)])
		writer.writerow(["Total remuneration", f"{sum((r['gross'] for r in rows), Decimal('0')):.2f}"])
		writer.writerow(["Total PCB", f"{sum((r['pcb'] for r in rows), Decimal('0')):.2f}"])
		writer.writerow(["Total CP38", f"{sum((r['cp38'] for r in rows), Decimal('0')):.2f}"])
		writer.writerow([])
		writer.writerow(["Employee", "Name", "Gross Remuneration", "PCB", "CP38"])
		for row in rows:
			writer.writerow(
				[row["employee"], row["employee_name"], f"{row['gross']:.2f}", f"{row['pcb']:.2f}", f"{row['cp38']:.2f}"]
			)
	return stream.getvalue().encode("utf-8-sig")


def _save_private_file(submission, filename: str, content: bytes) -> str:
	if submission.status in FROZEN_STATUSES:
		frappe.throw(_("Submitted files are immutable. Create a new revision."))
	old = frappe.get_all(
		"File",
		filters={
			"attached_to_doctype": submission.doctype,
			"attached_to_name": submission.name,
			"attached_to_field": "generated_file",
		},
		pluck="name",
	)
	for name in old:
		frappe.delete_doc("File", name, ignore_permissions=True, force=True)
	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": filename,
			"content": content,
			"is_private": 1,
			"attached_to_doctype": submission.doctype,
			"attached_to_name": submission.name,
			"attached_to_field": "generated_file",
		}
	)
	file_doc.save(ignore_permissions=True)
	return file_doc.file_url


def _portal_worksheet(submission, *, heading: str) -> bytes:
	"""Generate a human-reviewed portal handoff, never an asserted upload schema."""
	stream = io.StringIO(newline="")
	writer = csv.writer(stream, lineterminator="\r\n")
	writer.writerow([heading, "PORTAL PREPARATION WORKSHEET ONLY", submission.schema_version])
	writer.writerow(
		[
			"Employee",
			"Name",
			"Identity / Member No",
			"Levy-classified Wages",
			"Employee Amount",
			"Employer Amount",
			"Rule Version",
		]
	)
	for row in submission.employee_lines:
		writer.writerow(
			[
				row.employee,
				row.employee_name,
				row.agency_number or row.identity_number,
				f"{Decimal(str(row.wages or 0)):.2f}",
				f"{Decimal(str(row.employee_amount or 0)):.2f}",
				f"{Decimal(str(row.employer_amount or 0)):.2f}",
				row.rule_version,
			]
		)
	writer.writerow([])
	writer.writerow(["CONTROL TOTALS", submission.employee_count, submission.wage_total, submission.payable_total])
	return stream.getvalue().encode("utf-8-sig")


def _employer_references(submission) -> dict[str, str]:
	if not submission.employer_reference_snapshot:
		return {}
	try:
		value = parse_json_object(submission.employer_reference_snapshot, "Employer Reference Snapshot")
	except ValueError as exc:
		frappe.throw(_(str(exc)))
	return {str(key): str(item or "") for key, item in value.items()}


def generate_submission_file(submission):
	_ensure_permission()
	_ensure_company_access(submission.company)
	period_date = getdate(
		get_last_day(
			f"{int(submission.contribution_year):04d}-{int(submission.contribution_month or 12):02d}-01"
		)
	)
	assert_rule_review_current(submission.company, period_date)
	select_for_update("SELECT name FROM `tabStatutory Submission` WHERE name=%s", (submission.name,))
	submission.reload()
	if submission.status in FROZEN_STATUSES:
		frappe.throw(_("This submission is frozen. Create a new revision."))
	if submission.submission_mode == "API":
		frappe.throw(
			_(
				"No approved authority payroll-submission API adapter is installed. Use File Upload or Portal Only until the authority grants an official integration contract."
			)
		)
	prior_artifact = submission.generated_file
	prior_artifact_hash = submission.file_sha256
	prior_source_hash = submission.source_snapshot_hash
	prior_status = submission.status
	if submission.submission_type in MONTHLY_TYPES:
		errors = populate_submission_lines(submission)
		if errors:
			return {"status": "Validation Failed", "errors": errors}
		if prior_artifact and prior_source_hash == submission.source_snapshot_hash:
			submission.status = prior_status
			submission.save()
			return {
				"status": submission.status,
				"file_url": prior_artifact,
				"sha256": prior_artifact_hash,
				"source_snapshot_sha256": submission.source_snapshot_hash,
				"employee_count": submission.employee_count,
				"idempotent_replay": True,
			}
		if prior_artifact and prior_source_hash != submission.source_snapshot_hash:
			message = _(
				"Payroll or employer source data changed after file generation. The prior artifact was invalidated; review the new lines and generate again."
			)
			submission.generated_file = None
			submission.file_sha256 = None
			submission.status = "Validation Failed"
			submission.validation_errors = json.dumps([message], indent=2)
			submission.save()
			return {"status": "Validation Failed", "errors": [message], "source_changed": True}
		if not submission.employee_lines:
			submission.status = "Not Required"
			submission.generated_file = None
			submission.file_sha256 = None
			submission.generated_on = now_datetime()
			submission.generated_by = frappe.session.user
			submission.save()
			return {
				"status": "Not Required",
				"employee_count": 0,
				"message": _("No reportable employee lines were found for this authority and contribution month."),
			}
	elif submission.submission_type not in ANNUAL_PREPARATION_TYPES:
		frappe.throw(_("This submission type is generated from its source document print action."))

	references = _employer_references(submission)
	if not references:
		company = frappe.get_cached_doc("Company", submission.company)
		references = _company_reference_snapshot(company)
		submission.employer_reference_snapshot = json.dumps(references, sort_keys=True)

	if submission.submission_type == "Monthly PCB":
		hq_number = references.get("lhdn_hq_number", "")
		employer_number = references.get("lhdn_employer_number", "")
		if not hq_number or not employer_number:
			frappe.throw(_("Set LHDN HQ Number and Employer Number on the Company."))
		records = [
			LHDNPCBRecord(
				tin=row.tin,
				name=row.employee_name,
				old_ic=row.old_ic_number or "",
				new_ic=row.new_ic_number or "",
				passport=row.passport_number or "",
				country_code=row.country_code or "",
				mtd_amount=Decimal(str(row.mtd_amount or 0)),
				cp38_amount=Decimal(str(row.cp38_amount or 0)),
				employee_number=row.employee_number,
			)
			for row in submission.employee_lines
		]
		content = generate_lhdn_pcb_file(
			hq_number=hq_number,
			employer_number=employer_number,
			year=int(submission.contribution_year),
			month=int(submission.contribution_month),
			records=records,
		)
		# Exhibit 4 specifies xxxxxxxxxxmm_yyyy.txt where xxxxxxxxxx is the employer number.
		filename = (
			f"{digits(employer_number).zfill(10)[-10:]}"
			f"{int(submission.contribution_month):02d}_{int(submission.contribution_year):04d}.txt"
		)
	elif submission.submission_type == "EPF Form A":
		if submission.submission_mode == "File Upload":
			_ensure_legacy_epf_uat_enabled()
			submission.schema_version = "KWSP-ECARUMAN-LEGACY-CSV-UNVERIFIED"
			records = [
				EPFCSVRecord(
					member_number=row.agency_number,
					identity_number=row.identity_number,
					name=row.employee_name,
					wages=Decimal(str(row.wages or 0)),
					employer_share=Decimal(str(row.employer_amount or 0)),
					employee_share=Decimal(str(row.employee_amount or 0)),
				)
				for row in submission.employee_lines
			]
			content = generate_epf_csv(records)
			filename = f"EPF_LEGACY_ECARUMAN_UAT_{int(submission.contribution_year):04d}{int(submission.contribution_month):02d}.csv"
		else:
			submission.schema_version = SCHEMA_VERSIONS[submission.submission_type]
			content = _portal_worksheet(submission, heading="EPF i-Akaun (Employer)")
			filename = f"EPF_IAKAUN_PORTAL_WORKSHEET_{int(submission.contribution_year):04d}{int(submission.contribution_month):02d}.csv"
	elif submission.submission_type == "SOCSO EIS Combined":
		employer_code = references.get("socso_employer_code", "")
		registration_number = references.get("registration_number", "")
		if not employer_code or not registration_number:
			frappe.throw(_("Set SOCSO Employer Code and Company Registration Number on the Company."))
		data, _ = _monthly_employee_data(
			submission.company,
			int(submission.contribution_year),
			int(submission.contribution_month),
		)
		records = []
		for row in submission.employee_lines:
			item = data[row.employee]
			socso = item["results"].get("SOCSO", {})
			eis = item["results"].get("EIS", {})
			lindung = item["results"].get("LINDUNG 24 Jam", {})
			records.append(
				PERKESOCombinedRecord(
					employer_code=employer_code,
					company_registration_number=registration_number,
					employee_identity_number=row.identity_number,
					employee_name=row.employee_name,
					contribution_month=(
						f"{int(submission.contribution_month):02d}{int(submission.contribution_year):04d}"
					),
					wages=Decimal(str(row.wages or 0)),
					socso_employer=Decimal(str(socso.get("employer") or 0)),
					socso_employee=Decimal(str(socso.get("employee") or 0)),
					eis_employer=Decimal(str(eis.get("employer") or 0)),
					eis_employee=Decimal(str(eis.get("employee") or 0)),
					skbbk_employee=Decimal(str(lindung.get("extra") or 0)),
				)
			)
		content = generate_perkeso_combined_file(records)
		filename = (
			f"PERKESO_SOCSO_EIS_{int(submission.contribution_year):04d}"
			f"{int(submission.contribution_month):02d}.txt"
		)
	elif submission.submission_type == "HRD Levy":
		if not references.get("hrd_corp_registration_number"):
			frappe.throw(_("Set the HRD Corp Registration Number on the Company."))
		content = _portal_worksheet(submission, heading="HRD Corp Levy")
		filename = f"HRDCORP_LEVY_PORTAL_WORKSHEET_{int(submission.contribution_year):04d}{int(submission.contribution_month):02d}.csv"
	else:
		submission.schema_version = SCHEMA_VERSIONS[submission.submission_type]
		submission.portal_url = _portal_url(submission.authority)
		content = _annual_csv(submission)
		filename = (
			f"{submission.submission_type.replace(' ', '_').upper()}_PREPARATION_ONLY_"
			f"{int(submission.contribution_year):04d}_R{int(submission.revision or 0)}.csv"
		)

	file_url = _save_private_file(submission, filename, content)
	submission.generated_file = file_url
	submission.file_sha256 = sha256_bytes(content)
	submission.generated_on = now_datetime()
	submission.generated_by = frappe.session.user
	if (
		submission.submission_type in ANNUAL_PREPARATION_TYPES
		or submission.submission_mode == "Document Only"
	):
		# The bundled EPF serializer is deliberately UAT-only and must never be
		# presented as portal-ready until a current i-Akaun schema is verified.
		submission.status = "Generated"
	elif submission.submission_mode in {"File Upload", "Portal Only"}:
		submission.status = "Ready for Portal"
	else:
		submission.status = "Generated"
	submission.save()
	result = {
		"status": submission.status,
		"file_url": file_url,
		"sha256": submission.file_sha256,
		"source_snapshot_sha256": submission.source_snapshot_hash,
		"employee_count": submission.employee_count,
		"schema_version": submission.schema_version,
	}
	if submission.submission_type == "EPF Form A" and str(submission.schema_version).startswith("KWSP-ECARUMAN"):
		result["warning"] = _(
			"Legacy e-Caruman CSV generated for UAT only. It is not approved for the current i-Akaun (Employer) workflow."
		)
	return result
