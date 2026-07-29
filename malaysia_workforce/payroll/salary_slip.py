from __future__ import annotations

import calendar
import json
from datetime import date
from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import get_first_day, get_last_day, getdate

from malaysia_workforce.data_access import (
	get_malaysia_profile,
	get_scheme_treatment,
	get_work_agreement,
)
from malaysia_workforce.payroll.accumulator import remove_salary_slip_from_accumulator, update_accumulator_from_salary_slip
from malaysia_workforce.statutory.calculators import calculate_eis, calculate_epf, calculate_pcb, calculate_socso, determine_category
from malaysia_workforce.statutory.common import ContributionResult, PCBInput, ZERO, decimal, money, round_up_5_sen
from malaysia_workforce.statutory.snapshot import parse_statutory_snapshot

ENGINE_VERSION = "MW-STATUTORY-2026.1"


def _settings():
	return frappe.get_cached_doc("Malaysia Workforce Settings")


def _age_on(date_of_birth, on_date) -> int:
	born = getdate(date_of_birth)
	on_date = getdate(on_date)
	return on_date.year - born.year - ((on_date.month, on_date.day) < (born.month, born.day))


def _component_metadata(names: set[str]) -> dict[str, dict]:
	if not names:
		return {}
	rows = frappe.get_all(
		"Salary Component",
		filters={"name": ["in", list(names)]},
		fields=[
			"name",
			"salary_component_abbr",
			"depends_on_payment_days",
			"is_tax_applicable",
			"exempted_from_income_tax",
			"statistical_component",
			"do_not_include_in_total",
			"custom_include_in_epf_wages",
			"custom_include_in_socso_wages",
			"custom_include_in_eis_wages",
			"custom_include_in_pcb_remuneration",
			"custom_pcb_remuneration_type",
		],
	)
	return {row.name: row for row in rows}


def _classify_earnings(doc) -> dict[str, Decimal]:
	metadata = _component_metadata({row.salary_component for row in doc.earnings})
	bases = {"gross": ZERO, "epf": ZERO, "socso": ZERO, "eis": ZERO, "pcb_regular": ZERO, "pcb_additional": ZERO}
	for row in doc.earnings:
		amount = decimal(row.amount)
		meta = metadata.get(row.salary_component, {})
		if not meta.get("statistical_component") and not meta.get("do_not_include_in_total"):
			bases["gross"] += amount
		if meta.get("custom_include_in_epf_wages"):
			bases["epf"] += amount
		if meta.get("custom_include_in_socso_wages"):
			bases["socso"] += amount
		if meta.get("custom_include_in_eis_wages"):
			bases["eis"] += amount
		if meta.get("custom_include_in_pcb_remuneration"):
			remuneration_type = meta.get("custom_pcb_remuneration_type") or "Regular Remuneration"
			if remuneration_type == "Regular Remuneration":
				bases["pcb_regular"] += amount
			else:
				bases["pcb_additional"] += amount
	return {key: money(value) for key, value in bases.items()}


def _deduction_amount(doc, component: str) -> Decimal:
	return money(sum((decimal(row.amount) for row in doc.deductions if row.salary_component == component), ZERO))


def _parse_snapshot(row) -> dict:
	try:
		return parse_statutory_snapshot(row.custom_malaysia_statutory_snapshot)
	except ValueError as exc:
		frappe.throw(
			_("Submitted Salary Slip {0} has an invalid Malaysia statutory snapshot: {1}").format(
				row.name,
				exc,
			)
		)


def _historical_context(doc, settings) -> dict:
	year_start = date(getdate(doc.end_date).year, 1, 1)
	current_month_start = get_first_day(doc.end_date)
	slips = frappe.get_all(
		"Salary Slip",
		filters={
			"employee": doc.employee,
			"company": doc.company,
			"docstatus": 1,
			"end_date": ["between", [year_start, doc.end_date]],
			"name": ["!=", doc.name or ""],
		},
		fields=["name", "start_date", "end_date", "custom_malaysia_statutory_snapshot"],
		order_by="end_date asc",
		limit_page_length=500,
	)
	ctx = {
		"prior_month": {"gross": ZERO, "epf_relief": ZERO, "mtd": ZERO, "zakat": ZERO},
		"same_month_bases": {"gross": ZERO, "epf": ZERO, "socso": ZERO, "eis": ZERO, "pcb_regular": ZERO, "pcb_additional": ZERO},
		"same_month_deductions": {"EPF": ZERO, "SOCSO": ZERO, "LINDUNG 24 Jam": ZERO, "EIS": ZERO, "PCB": ZERO},
		"same_month_employer": {"EPF": ZERO, "SOCSO": ZERO, "EIS": ZERO},
	}
	for slip in slips:
		snapshot = _parse_snapshot(slip)
		bases = snapshot.get("current_wage_bases", {})
		results = snapshot.get("current_results", [])
		if getdate(slip.end_date) < current_month_start:
			ctx["prior_month"]["gross"] += decimal(bases.get("pcb_regular")) + decimal(bases.get("pcb_additional"))
			for result in results:
				if result.get("scheme") == "EPF":
					ctx["prior_month"]["epf_relief"] += decimal(result.get("employee_amount"))
				elif result.get("scheme") == "PCB":
					ctx["prior_month"]["mtd"] += decimal(result.get("employee_amount"))
			ctx["prior_month"]["zakat"] += decimal(snapshot.get("current_zakat"))
		else:
			for key in ctx["same_month_bases"]:
				ctx["same_month_bases"][key] += decimal(bases.get(key))
			for result in results:
				scheme = result.get("scheme")
				if scheme in ctx["same_month_deductions"]:
					ctx["same_month_deductions"][scheme] += decimal(result.get("employee_amount")) + decimal(result.get("extra_employee_amount"))
				if scheme in ctx["same_month_employer"]:
					ctx["same_month_employer"][scheme] += decimal(result.get("employer_amount"))
	return ctx


def _tax_declarations(employee: str, company: str, year: int, month: int) -> dict:
	out = {"tp3_gross": ZERO, "tp3_epf": ZERO, "tp3_mtd": ZERO, "tp3_zakat": ZERO, "tp3_reliefs": ZERO, "prior_tp1": ZERO, "current_tp1": ZERO}
	for row in frappe.get_all(
		"Malaysia Previous Employment TP3",
		filters={"employee": employee, "company": company, "tax_year": year, "status": "Accepted by Employer"},
		fields=["gross_normal_remuneration", "gross_additional_remuneration", "epf_contribution", "mtd_paid", "zakat_paid", "optional_reliefs"],
	):
		out["tp3_gross"] += decimal(row.gross_normal_remuneration) + decimal(row.gross_additional_remuneration)
		out["tp3_epf"] += decimal(row.epf_contribution)
		out["tp3_mtd"] += decimal(row.mtd_paid)
		out["tp3_zakat"] += decimal(row.zakat_paid)
		out["tp3_reliefs"] += decimal(row.optional_reliefs)
	declaration = frappe.db.get_value(
		"Malaysia Tax Declaration TP1",
		{"employee": employee, "company": company, "tax_year": year, "status": "Accepted by Employer"},
		"name",
		order_by="declaration_date desc, modified desc",
	)
	if declaration:
		for claim in frappe.get_all(
			"Malaysia Tax Relief Claim",
			filters={"parent": declaration, "parenttype": "Malaysia Tax Declaration TP1"},
			fields=["amount", "claim_month"],
		):
			claim_month = int(claim.claim_month or month)
			if claim_month < month:
				out["prior_tp1"] += decimal(claim.amount)
			elif claim_month == month:
				out["current_tp1"] += decimal(claim.amount)
	return out


def _not_applicable(scheme: str, wage_base: Decimal, reason: str) -> ContributionResult:
	return ContributionResult(scheme, money(wage_base), applicable=False, explanation=(reason or "Employee statutory setting: Not Applicable",))


def _treatment(employee: str, scheme: str, on_date, agreement) -> tuple[bool, str, str]:
	treatment, reason, notes = get_scheme_treatment(employee, scheme, on_date)
	if treatment == "Pending Review":
		frappe.throw(_("{0} treatment is Pending Review for employee {1}.").format(scheme, employee))
	if treatment == "Not Applicable":
		return False, treatment, reason or notes
	if treatment == "Automatic" and agreement and agreement.get("contract_relationship") == "Contract for Service":
		return False, treatment, "Automatic exclusion: Contract for Service"
	return True, treatment, reason or notes


def _current_delta(total: ContributionResult, prior_employee: Decimal, prior_employer: Decimal, *, extra_prior: Decimal = ZERO) -> ContributionResult:
	return ContributionResult(
		scheme=total.scheme,
		wage_base=total.wage_base,
		employee=money(total.employee - prior_employee),
		employer=money(total.employer - prior_employer),
		extra_employee=money(total.extra_employee - extra_prior),
		applicable=total.applicable,
		category=total.category,
		rule_version=total.rule_version,
		explanation=total.explanation + ("Current pay-run amount is the month-to-date total less prior submitted pay runs.",),
	)


def _result_dict(result: ContributionResult, treatment: str) -> dict:
	return {
		"scheme": result.scheme,
		"treatment": treatment,
		"applicable": int(result.applicable),
		"wage_base": str(result.wage_base),
		"employee_amount": str(result.employee),
		"employer_amount": str(result.employer),
		"extra_employee_amount": str(result.extra_employee),
		"category": result.category,
		"rule_version": result.rule_version,
		"explanation": "\n".join(result.explanation),
	}


def _append_deduction(doc, component: str, amount: Decimal):
	if amount == ZERO:
		return
	meta = frappe.db.get_value(
		"Salary Component",
		component,
		["salary_component_abbr", "depends_on_payment_days", "exempted_from_income_tax", "do_not_include_in_total", "statistical_component"],
		as_dict=True,
	)
	if not meta:
		frappe.throw(_("Salary Component {0} does not exist.").format(component))
	doc.append(
		"deductions",
		{
			"salary_component": component,
			"abbr": meta.salary_component_abbr,
			"amount": float(amount),
			"default_amount": float(amount),
			"depends_on_payment_days": meta.depends_on_payment_days,
			"exempted_from_income_tax": meta.exempted_from_income_tax,
			"do_not_include_in_total": meta.do_not_include_in_total,
			"statistical_component": meta.statistical_component,
		},
	)


def _is_final_pay_run(doc) -> bool:
	run_name = getattr(doc, "custom_malaysia_payroll_run", None)
	if run_name:
		value = frappe.db.get_value("Malaysia Payroll Run", run_name, "is_final_run_for_month")
		if value is not None:
			return bool(value)
	return getdate(doc.end_date) >= getdate(get_last_day(doc.end_date))


def apply_malaysia_statutory_calculations(doc, method=None):
	if doc.docstatus != 0 or getattr(doc, "custom_statutory_locked", 0):
		return
	if not frappe.db.get_value("Company", doc.company, "custom_enable_malaysia_payroll"):
		return
	settings = _settings()
	if settings.strict_rule_review and settings.rules_reviewed_through and getdate(doc.end_date) > getdate(settings.rules_reviewed_through):
		frappe.throw(
			_("Malaysia statutory rule review expired on {0}. Update Malaysia Workforce Settings before processing payroll.").format(settings.rules_reviewed_through)
		)
	profile = get_malaysia_profile(doc.employee, required=True)
	agreement = get_work_agreement(doc.employee, doc.end_date, required=True)
	if doc.payroll_entry:
		doc.custom_malaysia_payroll_run = frappe.db.get_value("Payroll Entry", doc.payroll_entry, "custom_malaysia_payroll_run")

	current = _classify_earnings(doc)
	history = _historical_context(doc, settings)
	month_bases = {key: money(decimal(history["same_month_bases"][key]) + decimal(current[key])) for key in current}
	current_zakat = _deduction_amount(doc, settings.zakat_component)
	current_cp38 = _deduction_amount(doc, settings.cp38_component)

	employee = frappe.db.get_value("Employee", doc.employee, ["date_of_birth"], as_dict=True)
	if not employee or not employee.date_of_birth:
		frappe.throw(
			_("Date of Birth is required on Employee {0} for Malaysian statutory calculations.").format(
				doc.employee
			)
		)
	age = _age_on(employee.date_of_birth, doc.end_date)
	epf_category = determine_category(
		citizenship_status=profile.nationality_status,
		age=age,
		legacy_foreign_opt_in=bool(profile.legacy_foreign_epf_opt_in),
	)
	extra_employee_rate = decimal(profile.employee_extra_epf_rate) / Decimal("100")
	extra_employer_rate = decimal(profile.employer_extra_epf_rate) / Decimal("100")

	month_total_results: list[dict] = []
	current_results: list[dict] = []

	# EPF
	epf_applies, epf_treatment, epf_reason = _treatment(doc.employee, "EPF", doc.end_date, agreement)
	if epf_applies:
		epf_total = calculate_epf(month_bases["epf"], epf_category, employee_extra_rate=extra_employee_rate, employer_extra_rate=extra_employer_rate)
	else:
		epf_total = _not_applicable("EPF", month_bases["epf"], epf_reason)
	epf_current = _current_delta(epf_total, history["same_month_deductions"]["EPF"], history["same_month_employer"]["EPF"])
	month_total_results.append(_result_dict(epf_total, epf_treatment))
	current_results.append(_result_dict(epf_current, epf_treatment))

	# SOCSO and LINDUNG 24 Jam/SKBBK are represented separately on the payslip and together in the PERKESO file.
	socso_applies, socso_treatment, socso_reason = _treatment(doc.employee, "SOCSO", doc.end_date, agreement)
	lindung_applies, lindung_treatment, lindung_reason = _treatment(doc.employee, "LINDUNG 24 Jam", doc.end_date, agreement)
	if profile.lindung_designation in {"Other Employer", "Not Applicable"} and lindung_treatment == "Automatic":
		lindung_applies = False
		lindung_reason = f"Employee designation: {profile.lindung_designation}"
	base_socso = calculate_socso(month_bases["socso"], profile.socso_category or "First")
	if socso_applies:
		socso_total = ContributionResult("SOCSO", base_socso.wage_base, base_socso.employee, base_socso.employer, ZERO, True, base_socso.category, base_socso.rule_version, base_socso.explanation)
	else:
		socso_total = _not_applicable("SOCSO", month_bases["socso"], socso_reason)
	if lindung_applies:
		lindung_total = ContributionResult("LINDUNG 24 Jam", base_socso.wage_base, ZERO, ZERO, base_socso.extra_employee, True, base_socso.category, base_socso.rule_version, base_socso.explanation)
	else:
		lindung_total = _not_applicable("LINDUNG 24 Jam", month_bases["socso"], lindung_reason)
	socso_current = _current_delta(socso_total, history["same_month_deductions"]["SOCSO"], history["same_month_employer"]["SOCSO"])
	lindung_current = _current_delta(lindung_total, ZERO, ZERO, extra_prior=history["same_month_deductions"]["LINDUNG 24 Jam"])
	month_total_results.extend([_result_dict(socso_total, socso_treatment), _result_dict(lindung_total, lindung_treatment)])
	current_results.extend([_result_dict(socso_current, socso_treatment), _result_dict(lindung_current, lindung_treatment)])

	# EIS
	eis_applies, eis_treatment, eis_reason = _treatment(doc.employee, "EIS", doc.end_date, agreement)
	if eis_treatment == "Automatic" and not profile.eis_eligible:
		eis_applies = False
		eis_reason = "Employee profile is not EIS eligible"
	if eis_applies:
		eis_total = calculate_eis(month_bases["eis"])
	else:
		eis_total = _not_applicable("EIS", month_bases["eis"], eis_reason)
	eis_current = _current_delta(eis_total, history["same_month_deductions"]["EIS"], history["same_month_employer"]["EIS"])
	month_total_results.append(_result_dict(eis_total, eis_treatment))
	current_results.append(_result_dict(eis_current, eis_treatment))

	# PCB
	pcb_applies, pcb_treatment, pcb_reason = _treatment(doc.employee, "PCB", doc.end_date, agreement)
	declarations = _tax_declarations(doc.employee, doc.company, getdate(doc.end_date).year, getdate(doc.end_date).month)
	month_number = getdate(doc.end_date).month
	is_final_run = _is_final_pay_run(doc)
	actual_month_normal = month_bases["pcb_regular"]
	period_days = max((getdate(doc.end_date) - getdate(doc.start_date)).days + 1, 1)
	days_in_month = calendar.monthrange(getdate(doc.end_date).year, month_number)[1]
	projected_month_normal = actual_month_normal
	if not is_final_run and period_days < days_in_month:
		projected_month_normal = max(actual_month_normal, money(decimal(current["pcb_regular"]) / Decimal(period_days) * Decimal(days_in_month)))

	# Estimate the EPF relief attributable to normal versus additional remuneration for PCB.
	projected_normal_epf = calculate_epf(projected_month_normal, epf_category).employee if epf_applies else ZERO
	projected_total_epf = calculate_epf(projected_month_normal + month_bases["pcb_additional"], epf_category).employee if epf_applies else ZERO
	projected_additional_epf = max(projected_total_epf - projected_normal_epf, ZERO)
	pcb_input = PCBInput(
		month=month_number,
		resident=bool(profile.tax_resident),
		category=int(profile.tax_category),
		current_normal_gross=projected_month_normal,
		current_additional_gross=month_bases["pcb_additional"],
		prior_gross=history["prior_month"]["gross"] + declarations["tp3_gross"],
		prior_epf_relief=history["prior_month"]["epf_relief"] + declarations["tp3_epf"],
		current_normal_epf=projected_normal_epf,
		current_additional_epf=projected_additional_epf,
		prior_optional_reliefs=declarations["tp3_reliefs"] + declarations["prior_tp1"],
		current_optional_reliefs=declarations["current_tp1"],
		prior_zakat=history["prior_month"]["zakat"] + declarations["tp3_zakat"],
		current_zakat=current_zakat,
		prior_mtd=history["prior_month"]["mtd"] + declarations["tp3_mtd"],
		child_units=decimal(profile.child_units),
		individual_disabled=bool(profile.individual_disabled),
		spouse_disabled=bool(profile.spouse_disabled),
		estimated_future_normal_gross=projected_month_normal,
		tax_regime=profile.tax_regime or "STANDARD",
	)
	if pcb_applies:
		pcb_full = calculate_pcb(pcb_input)
		method_name = settings.pcb_interim_method or "Cumulative Pro-Rata"
		if is_final_run or method_name == "Full Current Estimate":
			target_to_date = pcb_full.payable
		elif method_name == "Deduct on Final Pay Run":
			target_to_date = ZERO
		else:
			ratio = min(actual_month_normal / projected_month_normal, Decimal("1")) if projected_month_normal > ZERO else Decimal("1")
			target_to_date = round_up_5_sen(pcb_full.normal_mtd_after_zakat * ratio + pcb_full.additional_mtd)
		pcb_current_amount = money(target_to_date - history["same_month_deductions"]["PCB"])
		pcb_total_result = ContributionResult("PCB", month_bases["pcb_regular"] + month_bases["pcb_additional"], employee=pcb_full.payable, rule_version=pcb_full.rule_version, explanation=pcb_full.explanation)
		pcb_current_result = ContributionResult("PCB", current["pcb_regular"] + current["pcb_additional"], employee=pcb_current_amount, rule_version=pcb_full.rule_version, explanation=pcb_full.explanation + (f"Interim method: {method_name}",))
	else:
		pcb_full = None
		pcb_total_result = _not_applicable("PCB", month_bases["pcb_regular"] + month_bases["pcb_additional"], pcb_reason)
		pcb_current_result = _not_applicable("PCB", current["pcb_regular"] + current["pcb_additional"], pcb_reason)
	month_total_results.append(_result_dict(pcb_total_result, pcb_treatment))
	current_results.append(_result_dict(pcb_current_result, pcb_treatment))

	managed_components = {settings.epf_component, settings.socso_component, settings.skbbk_component, settings.eis_component, settings.pcb_component}
	doc.set("deductions", [row for row in doc.deductions if row.salary_component not in managed_components])
	_append_deduction(doc, settings.epf_component, epf_current.employee)
	_append_deduction(doc, settings.socso_component, socso_current.employee)
	_append_deduction(doc, settings.skbbk_component, lindung_current.extra_employee)
	_append_deduction(doc, settings.eis_component, eis_current.employee)
	_append_deduction(doc, settings.pcb_component, pcb_current_result.employee)

	doc.set("custom_malaysia_statutory_results", [])
	for result in current_results:
		doc.append("custom_malaysia_statutory_results", result)
	snapshot = {
		"engine_version": ENGINE_VERSION,
		"employee": doc.employee,
		"company": doc.company,
		"period": {"start": str(doc.start_date), "end": str(doc.end_date), "posting_date": str(doc.posting_date)},
		"current_wage_bases": {key: str(value) for key, value in current.items()},
		"month_cumulative_wage_bases": {key: str(value) for key, value in month_bases.items()},
		"current_results": current_results,
		"month_total_results": month_total_results,
		"current_zakat": str(current_zakat),
		"current_cp38": str(current_cp38),
		"pcb_input": {key: str(value) if isinstance(value, Decimal) else value for key, value in pcb_input.__dict__.items()},
		"pcb_result": pcb_full.to_dict() if pcb_full else None,
		"epf_category": epf_category,
		"is_final_pay_run_for_month": is_final_run,
	}
	doc.custom_malaysia_statutory_snapshot = json.dumps(snapshot, sort_keys=True, default=str)
	doc.custom_statutory_recalculation_required = 0
	# Core validation calculated totals before this hook. Recalculate after replacing deductions.
	doc.calculate_net_pay()
	doc.compute_year_to_date()
	doc.compute_month_to_date()
	doc.compute_component_wise_year_to_date()


def freeze_statutory_snapshot(doc, method=None):
	if not doc.custom_malaysia_statutory_snapshot:
		return
	doc.db_set("custom_statutory_locked", 1, update_modified=False)
	update_accumulator_from_salary_slip(doc)
	from malaysia_workforce.payroll.events import maybe_finalize_run_after_salary_slip_submit

	maybe_finalize_run_after_salary_slip_submit(doc)


def reopen_accumulator(doc, method=None):
	remove_salary_slip_from_accumulator(doc)
