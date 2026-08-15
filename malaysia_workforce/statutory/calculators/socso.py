from __future__ import annotations

from datetime import date
from decimal import Decimal

from malaysia_workforce.statutory.common import ContributionResult, ZERO, decimal, load_csv, money

RULE_VERSION = "PERKESO-ACT4-LINDUNG-2026-07-10"
WAGE_CEILING = Decimal("6000")
LINDUNG_START = date(2026, 6, 1)
LINDUNG_RELEASE_FROM = date(2026, 7, 8)


def calculate_socso(
	wages,
	category: str = "First",
	*,
	contribution_date: date | None = None,
	lindung_participation: str | None = None,
	lindung_effective_from: date | None = None,
) -> ContributionResult:
	"""SOCSO first/second category contribution, including LINDUNG 24 Jam (SKBBK).

	LINDUNG 24 Jam applies from 1 June 2026. PERKESO confirmed on 10 July 2026
	that release is an opt-out exercised by the employee: an employee who has
	recorded nothing participates. Contribution stops only from the effective
	date of the employee's own Liability Release Notice, which cannot take
	effect before the 8 July 2026 Cabinet decision, so already-deducted June
	contributions are never reversed.
	"""
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
		skbbk_band = money(row["first_employee_skbbk"])
	else:
		employee = ZERO
		employer = money(row["second_employer"])
		skbbk_band = money(row["second_employee_skbbk"])

	skbbk = ZERO
	released = False
	if contribution_date is not None and contribution_date >= LINDUNG_START:
		skbbk = skbbk_band
		if lindung_participation == "Not Participating" and lindung_effective_from is not None:
			if max(lindung_effective_from, LINDUNG_RELEASE_FROM) <= contribution_date:
				skbbk, released = ZERO, True

	if skbbk > ZERO:
		lindung_note = "LINDUNG 24 Jam applies by default; no effective Liability Release Notice is recorded"
	elif released:
		lindung_note = "LINDUNG 24 Jam stopped from the recorded PERKESO Liability Release Notice date"
	else:
		lindung_note = "LINDUNG 24 Jam does not apply to this contribution date"

	return ContributionResult(
		scheme="SOCSO",
		wage_base=wage_base,
		employee=employee,
		employer=employer,
		extra_employee=skbbk,
		category=category.title(),
		rule_version=RULE_VERSION,
		explanation=(
			"PERKESO scheduled contribution band",
			"Wages above RM6,000 use the ceiling band",
			lindung_note,
		),
	)
