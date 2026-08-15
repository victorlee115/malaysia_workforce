from __future__ import annotations

import json
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from malaysia_workforce.statutory.common import decimal, money

DATA = Path(__file__).resolve().parents[1] / "statutory" / "data" / "minimum_wage_2025.json"


def minimum_wage(on_date: date, *, employee_count: int = 10, professional_activity: bool = False) -> dict:
	rows = json.loads(DATA.read_text())["rates"]
	applicable = []
	for row in rows:
		start = date.fromisoformat(row["effective_from"])
		end = date.fromisoformat(row["effective_to"]) if row.get("effective_to") else date.max
		if not start <= on_date <= end:
			continue
		scope = row["scope"]
		if "Five or more" in scope and not (employee_count >= 5 or professional_activity):
			continue
		if "Fewer than five" in scope and (employee_count >= 5 or professional_activity):
			continue
		applicable.append(row)
	if not applicable:
		raise ValueError(f"No reviewed minimum-wage rule applies on {on_date}")
	row = applicable[-1]
	return {**row, "monthly": Decimal(row["monthly"]), "hourly": Decimal(row["hourly"])}


def validate_minimum_wage(wage_basis: str, rate, normal_hours_per_day, on_date: date,
	*, employee_count: int = 10, professional_activity: bool = False) -> None:
	rule = minimum_wage(on_date, employee_count=employee_count, professional_activity=professional_activity)
	contract_rate = decimal(rate)
	if wage_basis == "Monthly" and contract_rate < rule["monthly"]:
		raise ValueError(f"Monthly contract rate RM {contract_rate:.2f} is below the RM {rule['monthly']:.2f} minimum wage")
	if wage_basis == "Hourly" and contract_rate < rule["hourly"]:
		raise ValueError(f"Hourly contract rate RM {contract_rate:.2f} is below the RM {rule['hourly']:.2f} minimum wage")
	if wage_basis == "Daily" and contract_rate / decimal(normal_hours_per_day) < rule["hourly"]:
		raise ValueError("Daily contract rate is below the applicable hourly minimum wage equivalent")


def incomplete_month_wage(monthly_wage, eligible_calendar_days: int, calendar_days: int) -> Decimal:
	if calendar_days <= 0 or not 0 <= eligible_calendar_days <= calendar_days:
		raise ValueError("Eligible and calendar days are invalid")
	return money(decimal(monthly_wage) / Decimal(calendar_days) * Decimal(eligible_calendar_days))


def ordinary_hourly_rate(monthly_wage, normal_hours_per_day) -> Decimal:
	return money(decimal(monthly_wage) / Decimal("26") / decimal(normal_hours_per_day))


def overtime_pay(hourly_rate, hours) -> Decimal:
	return money(decimal(hourly_rate) * decimal(hours) * Decimal("1.5"))


def rest_day_work_pay(hourly_rate, hours, normal_hours, *, monthly_rated: bool) -> Decimal:
	rate, worked, normal = decimal(hourly_rate), decimal(hours), decimal(normal_hours)
	if min(rate, worked, normal) < 0 or normal == 0:
		raise ValueError("Rest-day inputs are invalid")
	if monthly_rated:
		base = rate * normal * (Decimal("0.5") if worked <= normal / 2 else Decimal("1"))
	else:
		base = rate * normal * (Decimal("1") if worked <= normal / 2 else Decimal("2"))
	return money(base + max(worked - normal, Decimal("0")) * rate * Decimal("2"))


def public_holiday_work_pay(hourly_rate, hours, normal_hours) -> Decimal:
	rate, worked, normal = decimal(hourly_rate), decimal(hours), decimal(normal_hours)
	if min(rate, worked, normal) < 0 or normal == 0:
		raise ValueError("Public-holiday inputs are invalid")
	if worked == 0:
		return Decimal("0.00")
	return money(normal * rate * Decimal("2") + max(worked - normal, Decimal("0")) * rate * Decimal("3"))


def part_time_additional_work_pay(hourly_rate, extra_hours, normal_hours, full_time_hours) -> Decimal:
	"""Regulation 5: 1x until the comparable full-time day, then 1.5x."""
	rate, extra = decimal(hourly_rate), decimal(extra_hours)
	normal, full_time = decimal(normal_hours), decimal(full_time_hours)
	if min(rate, extra, normal) < 0 or full_time <= normal:
		raise ValueError("Part-time additional-work inputs are invalid")
	ordinary_band = min(extra, full_time - normal)
	overtime_band = max(extra - ordinary_band, Decimal("0"))
	return money(ordinary_band * rate + overtime_band * rate * Decimal("1.5"))


def part_time_rest_day_work_pay(hourly_rate, hours, normal_hours, full_time_hours) -> Decimal:
	"""Regulation 9: two day-wages, then 1.5x/2x extra-hour bands."""
	rate, worked = decimal(hourly_rate), decimal(hours)
	normal, full_time = decimal(normal_hours), decimal(full_time_hours)
	if min(rate, worked, normal) < 0 or normal == 0 or full_time <= normal:
		raise ValueError("Part-time rest-day inputs are invalid")
	if worked == 0:
		return Decimal("0.00")
	extra = max(worked - normal, Decimal("0"))
	first = min(extra, full_time - normal)
	second = max(extra - first, Decimal("0"))
	return money(normal * rate * Decimal("2") + first * rate * Decimal("1.5") + second * rate * Decimal("2"))


def part_time_public_holiday_work_pay(hourly_rate, hours, normal_hours, full_time_hours) -> Decimal:
	"""Regulation 6: two day-wages in addition to holiday pay, then 2x/3x bands."""
	rate, worked = decimal(hourly_rate), decimal(hours)
	normal, full_time = decimal(normal_hours), decimal(full_time_hours)
	if min(rate, worked, normal) < 0 or normal == 0 or full_time <= normal:
		raise ValueError("Part-time public-holiday inputs are invalid")
	if worked == 0:
		return Decimal("0.00")
	extra = max(worked - normal, Decimal("0"))
	first = min(extra, full_time - normal)
	second = max(extra - first, Decimal("0"))
	return money(normal * rate * Decimal("2") + first * rate * Decimal("2") + second * rate * Decimal("3"))


def termination_benefit(last_twelve_month_wages, completed_years: int, additional_months: int = 0) -> Decimal:
	if completed_years < 0 or not 0 <= additional_months <= 11:
		raise ValueError("Service period is invalid")
	days = Decimal("10") if completed_years < 2 else Decimal("15") if completed_years < 5 else Decimal("20")
	service = Decimal(completed_years) + Decimal(additional_months) / Decimal("12")
	daily = decimal(last_twelve_month_wages) / Decimal("365")
	return (daily * days * service).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
