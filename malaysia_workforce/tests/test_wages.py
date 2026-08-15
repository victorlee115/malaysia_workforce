from datetime import date
from decimal import Decimal

from malaysia_workforce.payroll.wages import (
	incomplete_month_wage,
	minimum_wage,
	ordinary_hourly_rate,
	overtime_pay,
	part_time_additional_work_pay,
	part_time_public_holiday_work_pay,
	part_time_rest_day_work_pay,
	public_holiday_work_pay,
	rest_day_work_pay,
	termination_benefit,
	validate_minimum_wage,
)
from malaysia_workforce.tests._assertions import raises


def test_minimum_wage_effective_boundaries_and_small_employer_transition():
	assert minimum_wage(date(2025, 1, 31))["monthly"] == Decimal("1500")
	assert minimum_wage(date(2025, 2, 1), employee_count=10)["monthly"] == Decimal("1700")
	assert minimum_wage(date(2025, 2, 1), employee_count=4)["monthly"] == Decimal("1500")
	assert minimum_wage(date(2025, 8, 1), employee_count=1)["monthly"] == Decimal("1700")


def test_minimum_wage_validation_for_monthly_daily_and_hourly_rates():
	validate_minimum_wage("Monthly", 1700, 8, date(2026, 1, 1))
	validate_minimum_wage("Hourly", "8.72", 8, date(2026, 1, 1))
	validate_minimum_wage("Daily", "69.76", 8, date(2026, 1, 1))
	with raises(ValueError, match="below"):
		validate_minimum_wage("Hourly", "8.71", 8, date(2026, 1, 1))


def test_incomplete_month_uses_calendar_days():
	assert incomplete_month_wage(1700, 15, 31) == Decimal("822.58")


def test_overtime_rest_day_and_public_holiday_pay():
	rate = ordinary_hourly_rate(2600, 8)
	assert rate == Decimal("12.50")
	assert overtime_pay(rate, 2) == Decimal("37.50")
	assert rest_day_work_pay(rate, 4, 8, monthly_rated=True) == Decimal("50.00")
	assert rest_day_work_pay(rate, 8, 8, monthly_rated=True) == Decimal("100.00")
	assert rest_day_work_pay(rate, 10, 8, monthly_rated=True) == Decimal("150.00")
	assert public_holiday_work_pay(rate, 8, 8) == Decimal("200.00")
	assert public_holiday_work_pay(rate, 10, 8) == Decimal("275.00")
	assert public_holiday_work_pay(rate, 2, 8) == Decimal("200.00")
	assert public_holiday_work_pay(rate, 0, 8) == Decimal("0.00")


def test_part_time_additional_work_bands():
	assert part_time_additional_work_pay("10", "2", "4", "8") == Decimal("20.00")
	assert part_time_additional_work_pay("10", "6", "4", "8") == Decimal("70.00")


def test_part_time_rest_day_bands():
	assert part_time_rest_day_work_pay("10", "4", "4", "8") == Decimal("80.00")
	assert part_time_rest_day_work_pay("10", "10", "4", "8") == Decimal("180.00")


def test_part_time_public_holiday_bands():
	assert part_time_public_holiday_work_pay("10", "4", "4", "8") == Decimal("80.00")
	assert part_time_public_holiday_work_pay("10", "10", "4", "8") == Decimal("220.00")


def test_termination_benefit_ten_fifteen_twenty_day_bands():
	assert termination_benefit(36500, 1) == Decimal("1000.00")
	assert termination_benefit(36500, 2) == Decimal("3000.00")
	assert termination_benefit(36500, 5) == Decimal("10000.00")
