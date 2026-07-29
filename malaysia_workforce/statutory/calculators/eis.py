from __future__ import annotations

from decimal import Decimal

from malaysia_workforce.statutory.common import ContributionResult, ZERO, decimal, load_csv, money

RULE_VERSION = "PERKESO-ACT800-2024-10"
WAGE_CEILING = Decimal("6000")


def calculate_eis(wages) -> ContributionResult:
	wage_base = max(money(wages), ZERO)
	if wage_base <= ZERO:
		return ContributionResult("EIS", wage_base, rule_version=RULE_VERSION)
	lookup_wage = min(wage_base, WAGE_CEILING + Decimal("0.01"))
	row = next(
		(
			item
			for item in load_csv("eis_2024.csv")
			if decimal(item["wage_from"]) <= lookup_wage <= decimal(item["wage_to"])
		),
		None,
	)
	if row is None:
		raise ValueError(f"No EIS contribution band for wages {wage_base}")
	return ContributionResult(
		scheme="EIS",
		wage_base=wage_base,
		employee=money(row["employee"]),
		employer=money(row["employer"]),
		category="Act 800",
		rule_version=RULE_VERSION,
		explanation=("PERKESO EIS scheduled contribution band", "Wages above RM6,000 use the ceiling band"),
	)
