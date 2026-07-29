from __future__ import annotations

from datetime import date
from decimal import Decimal

from malaysia_workforce.statutory.common import (
	ContributionResult,
	ZERO,
	ceil_ringgit,
	decimal,
	load_csv,
	money,
)

RULE_VERSION = "KWSP-THIRD-SCHEDULE-2025-10"
TABLE_LIMIT = Decimal("20000")

CATEGORY_CONFIG = {
	"A": {"file": "epf_part_a_2025.csv", "employee_rate": Decimal("0.11"), "employer_rate": Decimal("0.12")},
	"C": {"file": "epf_part_c_2025.csv", "employee_rate": Decimal("0.055"), "employer_rate": Decimal("0.06")},
	"E": {"file": "epf_part_e_2025.csv", "employee_rate": Decimal("0"), "employer_rate": Decimal("0.04")},
	"F": {"file": None, "employee_rate": Decimal("0.02"), "employer_rate": Decimal("0.02")},
}


def determine_category(*, citizenship_status: str, age: int, legacy_foreign_opt_in: bool = False) -> str:
	status = citizenship_status.strip().lower()
	if status in {"malaysian", "citizen", "malaysian citizen"}:
		return "E" if age >= 60 else "A"
	if status in {"permanent resident", "pr", "malaysia permanent resident"} or legacy_foreign_opt_in:
		return "C" if age >= 60 else "A"
	return "F"


def _table_result(wages: Decimal, category: str) -> tuple[Decimal, Decimal]:
	rows = load_csv(CATEGORY_CONFIG[category]["file"])
	for row in rows:
		if decimal(row["wage_from"]) <= wages <= decimal(row["wage_to"]):
			return money(row["employee"]), money(row["employer"])
	raise ValueError(f"No EPF contribution band for wages {wages} in Part {category}")


def calculate_epf(wages, category: str, *, employee_extra_rate=0, employer_extra_rate=0) -> ContributionResult:
	wage_base = max(money(wages), ZERO)
	category = category.upper().strip()
	if category not in CATEGORY_CONFIG:
		raise ValueError(f"Unsupported EPF category: {category}")
	if wage_base <= ZERO:
		return ContributionResult("EPF", wage_base, category=category, rule_version=RULE_VERSION)

	config = CATEGORY_CONFIG[category]
	if category != "F" and wage_base <= TABLE_LIMIT:
		employee, employer = _table_result(wage_base, category)
		explanation = (f"Third Schedule Part {category} table band",)
	else:
		employee = ceil_ringgit(wage_base * config["employee_rate"])
		employer = ceil_ringgit(wage_base * config["employer_rate"])
		explanation = (
			f"Percentage method under Third Schedule Part {category}",
			"Each payable share containing sen is rounded up to the next ringgit",
		)

	if decimal(employee_extra_rate) > 0:
		employee = ceil_ringgit(employee + wage_base * decimal(employee_extra_rate))
	if decimal(employer_extra_rate) > 0:
		employer = ceil_ringgit(employer + wage_base * decimal(employer_extra_rate))

	return ContributionResult(
		scheme="EPF",
		wage_base=wage_base,
		employee=money(employee),
		employer=money(employer),
		category=category,
		rule_version=RULE_VERSION,
		explanation=explanation,
	)
