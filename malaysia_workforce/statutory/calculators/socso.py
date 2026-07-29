from __future__ import annotations

from decimal import Decimal

from malaysia_workforce.statutory.common import ContributionResult, ZERO, decimal, load_csv, money

RULE_VERSION = "PERKESO-ACT4-SKBBK-2026-06"
WAGE_CEILING = Decimal("6000")


def calculate_socso(wages, category: str = "First") -> ContributionResult:
	wage_base = max(money(wages), ZERO)
	category_normalized = category.strip().lower()
	if category_normalized not in {"first", "second"}:
		raise ValueError("SOCSO category must be 'First' or 'Second'")
	if wage_base <= ZERO:
		return ContributionResult("SOCSO", wage_base, category=category.title(), rule_version=RULE_VERSION)

	lookup_wage = min(wage_base, WAGE_CEILING + Decimal("0.01"))
	row = next(
		(
			item
			for item in load_csv("socso_skbbk_2026.csv")
			if decimal(item["wage_from"]) <= lookup_wage <= decimal(item["wage_to"])
		),
		None,
	)
	if row is None:
		raise ValueError(f"No SOCSO contribution band for wages {wage_base}")

	if category_normalized == "first":
		employee = money(row["first_employee_invalidity"])
		employer = money(row["first_employer"])
		skbbk = money(row["first_employee_skbbk"])
	else:
		employee = ZERO
		employer = money(row["second_employer"])
		skbbk = money(row["second_employee_skbbk"])

	return ContributionResult(
		scheme="SOCSO",
		wage_base=wage_base,
		employee=employee,
		employer=employer,
		extra_employee=skbbk,
		category=category.title(),
		rule_version=RULE_VERSION,
		explanation=("PERKESO scheduled contribution band", "Wages above RM6,000 use the ceiling band"),
	)
