from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import formatdate, getdate

from malaysia_workforce.statutory.calculators.socso import LINDUNG_RELEASE_FROM

LINDUNG_EXISTING_EMPLOYEE_CUTOFF = date(2026, 7, 8)
LINDUNG_EXISTING_RELEASE_FROM = date(2026, 7, 13)
LINDUNG_EXISTING_RELEASE_THROUGH = date(2026, 8, 31)


def _enabled_company(company: str | None) -> bool:
	return bool(company and frappe.db.get_value("Company", company, "custom_enable_malaysia_payroll"))


def validate_company(doc, method=None):
	if not doc.get("custom_enable_malaysia_payroll"):
		return
	if doc.country != "Malaysia" or doc.get("custom_malaysia_jurisdiction") != "Peninsular Malaysia":
		frappe.throw(_("Phase 1 Malaysia Payroll supports Peninsular Malaysian companies only."))
	issues = hrd_registration_issues(doc.name, getdate(), company_doc=doc)
	if issues:
		frappe.throw("<br>".join(issues))


def validate_employee(doc, method=None):
	if not _enabled_company(doc.company):
		return
	if frappe.db.get_value("Company", doc.company, "country") != "Malaysia":
		frappe.throw(_("Statutory payroll can only be enabled for a Malaysian Company."))
	if doc.get("custom_malaysia_citizenship_status") and doc.get("custom_malaysia_citizenship_status") not in {
		"Malaysian Citizen",
		"Permanent Resident",
	}:
		frappe.throw(_("Phase 1 supports Malaysian citizens and permanent residents only."))
	issues = lindung_release_issues(doc)
	if issues:
		frappe.throw("<br>".join(issues))


def lindung_release_issues(doc) -> list[str]:
	"""Return fail-closed validation errors for a recorded liability release.

	LINDUNG 24 Jam participation is the statutory default, so nothing is
	required to stay in the scheme. Leaving it is the affirmative act and needs
	the employee's own Liability Release Notice behind it.
	"""
	if doc.get("custom_lindung_participation") != "Not Participating":
		return []
	issues: list[str] = []
	if not doc.get("custom_lindung_effective_from"):
		issues.append(_("Record the effective date of the employee's PERKESO Liability Release Notice."))
	if not doc.get("custom_lindung_evidence"):
		issues.append(
			_("Attach the employee's PERKESO Liability Release Notice. The employer may not file it on their behalf.")
		)
	registration_date = doc.get("custom_lindung_registration_date")
	if not registration_date:
		issues.append(_("Record the employee's PERKESO registration date for the LINDUNG release window."))
	if not doc.get("custom_lindung_effective_from") or not registration_date:
		return issues

	effective = getdate(doc.custom_lindung_effective_from)
	registered = getdate(registration_date)
	if effective < LINDUNG_RELEASE_FROM:
		issues.append(
			_("A LINDUNG 24 Jam Liability Release Notice cannot take effect before {0}.").format(
				formatdate(LINDUNG_RELEASE_FROM)
			)
		)
	if registered <= LINDUNG_EXISTING_EMPLOYEE_CUTOFF:
		if not LINDUNG_EXISTING_RELEASE_FROM <= effective <= LINDUNG_EXISTING_RELEASE_THROUGH:
			issues.append(
				_("An existing employee's release must be dated from {0} through {1}.").format(
					formatdate(LINDUNG_EXISTING_RELEASE_FROM),
					formatdate(LINDUNG_EXISTING_RELEASE_THROUGH),
				)
			)
	elif not registered <= effective <= registered + timedelta(days=30):
		issues.append(
			_("A newly registered employee's release must be dated within 30 days of PERKESO registration.")
		)
	return issues


def lindung_payroll_issues(doc) -> list[str]:
	issues = lindung_release_issues(doc)
	if doc.get("custom_lindung_multiple_employers"):
		issues.append(
			_("LINDUNG payroll for an employee with multiple employers is outside the reviewed phase 1 scope. Payroll is stopped rather than guessing PERKESO's selected employer.")
		)
	return issues


def active_malaysian_employee_count(company: str, on_date) -> int:
	"""Count Malaysian citizens employed on a date for the HRD threshold."""
	on_date = getdate(on_date)
	rows = frappe.get_all(
		"Employee",
		filters={"company": company, "custom_malaysia_citizenship_status": "Malaysian Citizen"},
		fields=["status", "date_of_joining", "relieving_date"],
	)
	count = 0
	for row in rows:
		if row.date_of_joining and getdate(row.date_of_joining) > on_date:
			continue
		if row.relieving_date and getdate(row.relieving_date) < on_date:
			continue
		if row.status != "Active" and not row.relieving_date:
			continue
		count += 1
	return count


def hrd_registration_issues(company: str, on_date, *, company_doc=None) -> list[str]:
	company_doc = company_doc or frappe.get_cached_doc("Company", company)
	count = active_malaysian_employee_count(company, on_date)
	return hrd_registration_issues_for_count(company_doc, count, on_date)


def hrd_registration_issues_for_count(company_doc, count: int, on_date) -> list[str]:
	registration_class = company_doc.get("custom_hrd_registration_class") or "Not Registered"
	issues: list[str] = []
	if count >= 10 and registration_class != "Compulsory (1%)":
		issues.append(
			_("HRD Corp registration must be Compulsory (1%) because {0} Malaysian employees are employed on the payroll date.").format(count)
		)
	if registration_class in {"Optional (0.5%)", "Compulsory (1%)"}:
		if not company_doc.get("custom_hrd_registration_number") or not company_doc.get("custom_hrd_effective_from"):
			issues.append(_("Complete the HRD Corp registration number and effective date."))
		elif count >= 10 and getdate(company_doc.custom_hrd_effective_from) > getdate(on_date):
			issues.append(_("The HRD Corp registration is not effective for this payroll date."))
	return issues


def unclassified_earning_components(component_names) -> list[str]:
	names = sorted({name for name in component_names if name})
	if not names:
		return []
	rows = frappe.get_all(
		"Salary Component",
		filters={"name": ["in", names], "type": "Earning"},
		fields=["name", "statistical_component", "do_not_include_in_total", "custom_pcb_treatment"],
	)
	return sorted(
		row.name
		for row in rows
		if not row.statistical_component and not row.do_not_include_in_total and not row.custom_pcb_treatment
	)


def validate_contract(doc, method=None):
	if doc.party_type != "Employee" or not doc.party_name:
		return
	company = frappe.db.get_value("Employee", doc.party_name, "company")
	if not _enabled_company(company):
		return
	if doc.status != "Active":
		return
	for field, label in (
		("custom_malaysia_wage_basis", "Wage Basis"),
		("custom_malaysia_work_classification", "Work Classification"),
		("custom_normal_hours_per_day", "Normal Hours per Day"),
		("custom_normal_hours_per_week", "Normal Hours per Week"),
		("custom_rest_day", "Rest Day"),
	):
		if not doc.get(field):
			frappe.throw(_("{0} is required for an active Malaysian employment Contract.").format(label))
	if doc.custom_malaysia_wage_basis in {"Daily", "Hourly"} and not doc.custom_contract_wage_rate:
		frappe.throw(_("Daily or Hourly Rate is required for this active Contract."))
	if Decimal(str(doc.custom_normal_hours_per_day)) > Decimal("8"):
		frappe.throw(_("Normal Hours per Day cannot exceed 8."))
	if Decimal(str(doc.custom_normal_hours_per_week)) > Decimal("45"):
		frappe.throw(_("Normal Hours per Week cannot exceed 45."))
	if doc.custom_malaysia_work_classification == "Part-time":
		if not doc.custom_comparable_full_time_hours_per_day or not doc.custom_comparable_full_time_hours:
			frappe.throw(_("Comparable Full-time daily and weekly hours are required for a part-time Contract."))
		if Decimal(str(doc.custom_comparable_full_time_hours_per_day)) > Decimal("8"):
			frappe.throw(_("Comparable Full-time Hours per Day cannot exceed 8."))
		if Decimal(str(doc.custom_comparable_full_time_hours)) > Decimal("45"):
			frappe.throw(_("Comparable Full-time Hours per Week cannot exceed 45."))
		if Decimal(str(doc.custom_comparable_full_time_hours_per_day)) <= Decimal(str(doc.custom_normal_hours_per_day)):
			frappe.throw(_("Comparable Full-time Hours per Day must exceed the part-time normal hours."))
		if Decimal(str(doc.custom_comparable_full_time_hours)) <= Decimal(str(doc.custom_normal_hours_per_week)):
			frappe.throw(_("Comparable Full-time Hours per Week must exceed the part-time normal hours."))


def validate_salary_component(doc, method=None):
	if doc.type == "Earning":
		classified = any(
			doc.get(field)
			for field in (
				"custom_include_in_epf_wages",
				"custom_include_in_socso_wages",
				"custom_include_in_eis_wages",
				"custom_include_in_hrd_levy_wages",
				"custom_include_in_ordinary_rate",
			)
		)
		if classified and not doc.get("custom_pcb_treatment"):
			frappe.throw(_("Select the PCB Treatment for this Malaysian earning component."))
