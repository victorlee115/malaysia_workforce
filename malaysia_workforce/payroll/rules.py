from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

MINIMUM_WAGE_PATH = Path(__file__).resolve().parents[1] / "statutory" / "data" / "minimum_wage_2025.json"
PAY_RULE_PATH = Path(__file__).resolve().parents[1] / "statutory" / "data" / "pay_rules_2026.json"


@lru_cache(maxsize=1)
def _minimum_wage_data() -> dict:
	return json.loads(MINIMUM_WAGE_PATH.read_text(encoding="utf-8"))


def minimum_hourly_wage(on_date: date) -> Decimal:
	applicable = [
		row
		for row in _minimum_wage_data()["rates"]
		if date.fromisoformat(row["effective_from"]) <= on_date
	]
	if not applicable:
		raise ValueError(f"No reviewed minimum-wage rule is installed for {on_date.isoformat()}")
	return Decimal(str(applicable[-1]["hourly"]))


@lru_cache(maxsize=1)
def _pay_rule_data() -> dict:
	return json.loads(PAY_RULE_PATH.read_text(encoding="utf-8"))


def pay_rule_for_date(on_date: date, classification: str) -> dict:
	applicable = [
		row
		for row in _pay_rule_data()["rules"]
		if row["classification"] == classification
		and date.fromisoformat(row["effective_from"]) <= on_date
	]
	if not applicable:
		raise ValueError(
			f"No reviewed {classification} pay rule is installed for {on_date.isoformat()}"
		)
	return applicable[-1].copy()


def validate_flexible_worker_classification(
	*,
	work_arrangement: str,
	pay_basis: str,
	regularity: str,
	normal_weekly_hours: Decimal,
	comparable_full_time_weekly_hours: Decimal,
) -> str:
	if pay_basis != "Hourly":
		raise ValueError("Flexible staffing pay generation supports Hourly agreements only; use standard HRMS payroll for other pay bases")
	if comparable_full_time_weekly_hours <= 0:
		raise ValueError("Comparable full-time weekly hours must be greater than zero")
	ratio = normal_weekly_hours / comparable_full_time_weekly_hours
	if work_arrangement == "Part Time":
		if ratio <= Decimal("0.30") or ratio > Decimal("0.70"):
			raise ValueError(
				"Part Time weekly hours must be more than 30% and not more than 70% of comparable full-time hours"
			)
		return "PART_TIME_REGULATIONS_2010"
	if work_arrangement == "Casual":
		if regularity != "Occasional or Irregular" or ratio > Decimal("0.30"):
			raise ValueError(
				"Casual classification requires occasional or irregular work not exceeding 30% of comparable full-time hours"
			)
		return "CASUAL_CONTRACT_RATE"
	if work_arrangement == "Full Time":
		raise ValueError("Full Time payroll remains in standard Frappe HR and is not generated from Staffing Plan hours")
	raise ValueError(f"Unsupported work arrangement: {work_arrangement or 'Not Set'}")
