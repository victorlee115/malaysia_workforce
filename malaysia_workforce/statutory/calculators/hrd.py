from __future__ import annotations

from decimal import Decimal

from malaysia_workforce.statutory.common import ContributionResult, ZERO, decimal, money


RULE_VERSION = "HRDCORP-LEVY-2026-01"


def calculate_hrd_levy(wages, rate_percent=Decimal("1"), *, registered: bool = True) -> ContributionResult:
	"""Return the employer-only HRD Corp levy for explicitly classified wages.

	Eligibility and wage classification remain company/Salary Component controls;
	this pure function intentionally performs no headcount or registration guessing.
	"""
	wage_base = money(wages)
	rate = decimal(rate_percent)
	if wage_base < ZERO:
		raise ValueError("HRD Corp levy wages cannot be negative")
	if rate < ZERO or rate > Decimal("100"):
		raise ValueError("HRD Corp levy rate must be between 0 and 100 percent")
	if not registered or wage_base == ZERO:
		return ContributionResult(
			"HRD Corp",
			wage_base,
			applicable=False,
			rule_version=RULE_VERSION,
			explanation=("Company is not registered or no levy-classified wages were present.",),
		)
	return ContributionResult(
		"HRD Corp",
		wage_base,
		employer=money(wage_base * rate / Decimal("100")),
		rule_version=RULE_VERSION,
		explanation=(f"Employer levy calculated at {rate}% on explicitly classified wages.",),
	)
