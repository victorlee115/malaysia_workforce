from datetime import date
from decimal import Decimal

from malaysia_workforce.tests._assertions import raises

from malaysia_workforce.forms.validation import load_tp1_relief_rules, validate_tp1_rows
from malaysia_workforce.payroll.rules import minimum_hourly_wage, pay_rule_for_date, validate_flexible_worker_classification
from malaysia_workforce.statutory.calculators.hrd import calculate_hrd_levy
from malaysia_workforce.statutory.calculators.pcb import calculate_pcb
from malaysia_workforce.statutory.common import PCBInput


def test_hrd_levy_is_employer_only_and_deterministic():
	result = calculate_hrd_levy("12345.67", "1", registered=True)
	assert result.employee == Decimal("0.00")
	assert result.employer == Decimal("123.46")
	assert result.wage_base == Decimal("12345.67")
	assert result.rule_version == "HRDCORP-LEVY-2026-01"


def test_hrd_levy_rejects_invalid_rates_and_unregistered_company_is_not_applicable():
	with raises(ValueError, match="between 0 and 100"):
		calculate_hrd_levy(1000, 101)
	assert not calculate_hrd_levy(1000, 1, registered=False).applicable


def test_effective_minimum_wage_and_classification_boundaries():
	assert minimum_hourly_wage(date(2025, 2, 1)) == Decimal("8.72")
	with raises(ValueError, match="No reviewed"):
		minimum_hourly_wage(date(2025, 1, 31))
	assert (
		validate_flexible_worker_classification(
			work_arrangement="Part Time",
			pay_basis="Hourly",
			regularity="Regular Variable",
			normal_weekly_hours=Decimal("31.5"),
			comparable_full_time_weekly_hours=Decimal("45"),
		)
		== "PART_TIME_REGULATIONS_2010"
	)
	with raises(ValueError, match="more than 30%"):
		validate_flexible_worker_classification(
			work_arrangement="Part Time",
			pay_basis="Hourly",
			regularity="Regular Variable",
			normal_weekly_hours=Decimal("13.5"),
			comparable_full_time_weekly_hours=Decimal("45"),
		)
	assert (
		validate_flexible_worker_classification(
			work_arrangement="Casual",
			pay_basis="Hourly",
			regularity="Occasional or Irregular",
			normal_weekly_hours=Decimal("13.5"),
			comparable_full_time_weekly_hours=Decimal("45"),
		)
		== "CASUAL_CONTRACT_RATE"
	)
	assert pay_rule_for_date(date(2026, 8, 1), "PART_TIME_REGULATIONS_2010")["overtime_multiplier"] == "1.5"
	with raises(ValueError, match="No reviewed"):
		pay_rule_for_date(date(2010, 9, 30), "PART_TIME_REGULATIONS_2010")


def test_tp1_catalogue_controls_codes_caps_and_duplicate_evidence():
	rules = load_tp1_relief_rules(2026)
	assert set(rules) == {
		"C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10",
		"C11", "C12", "C13", "C14", "C15", "C16A", "C16B", "C17",
	}
	with raises(ValueError, match="not a valid TP1 code"):
		validate_tp1_rows([{"relief_code": "C99", "amount": 1, "evidence_reference": "R1"}])
	with raises(ValueError, match="annual limit"):
		validate_tp1_rows([{"relief_code": "C14", "amount": 351, "evidence_reference": "R1"}])
	with raises(ValueError, match="duplicate evidence"):
		validate_tp1_rows(
			[
				{"relief_code": "C5", "amount": 100, "evidence_reference": "same"},
				{"relief_code": "C5", "amount": 100, "evidence_reference": "SAME"},
			]
		)


def test_pcb_special_regimes_fail_closed_for_residents_and_nonresidents():
	for resident in (True, False):
		with raises(ValueError, match="not implemented"):
			calculate_pcb(
				PCBInput(
					month=8,
					resident=resident,
					category=1,
					current_normal_gross=Decimal("5000"),
					tax_regime="RETURNING_EXPERT",
				)
			)
