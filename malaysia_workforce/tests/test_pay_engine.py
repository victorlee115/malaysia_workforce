from datetime import datetime
from decimal import Decimal

from malaysia_workforce.tests._assertions import raises

from malaysia_workforce.payroll.pay_engine import ShiftPayInput, calculate_shift_pay


def args(**overrides):
	values = {
		"actual_start": datetime(2026, 8, 1, 8, 0),
		"actual_end": datetime(2026, 8, 1, 18, 0),
		"hourly_rate": Decimal("12.00"),
		"normal_part_time_daily_hours": Decimal("6"),
		"comparable_full_time_daily_hours": Decimal("8"),
	}
	values.update(overrides)
	return ShiftPayInput(**values)


def test_ordinary_additional_and_overtime_bands():
	result = calculate_shift_pay(args())
	assert result.ordinary_hours == Decimal("6.00")
	assert result.additional_hours == Decimal("2.00")
	assert result.overtime_hours == Decimal("2.00")
	assert result.gross_pay == Decimal("132.00")
	assert [line.component for line in result.lines] == [
		"Casual Ordinary Pay",
		"Part-Time Additional Hours",
		"Casual Overtime Pay",
	]


def test_rest_day_multipliers():
	result = calculate_shift_pay(args(is_rest_day=True))
	assert result.gross_pay == Decimal("228.00")


def test_public_holiday_multipliers():
	result = calculate_shift_pay(args(is_public_holiday=True))
	assert result.gross_pay == Decimal("336.00")


def test_unpaid_break_reduces_payable_time():
	result = calculate_shift_pay(args(unpaid_break_minutes=60))
	assert result.payable_hours == Decimal("9.00")
	assert result.gross_pay == Decimal("114.00")


def test_invalid_time_rejected():
	with raises(ValueError, match="after"):
		calculate_shift_pay(args(actual_end=datetime(2026, 8, 1, 7, 0)))


def test_auto_verified_capped_time_does_not_pay_unapproved_early_or_late_time():
	from malaysia_workforce.payroll.pay_engine import select_pay_interval

	start, end, basis = select_pay_interval(
		actual_start=datetime(2026, 8, 1, 7, 45),
		actual_end=datetime(2026, 8, 1, 18, 15),
		scheduled_start=datetime(2026, 8, 1, 8, 0),
		scheduled_end=datetime(2026, 8, 1, 18, 0),
		status="Automatically Verified",
	)
	assert (start, end, basis) == (
		datetime(2026, 8, 1, 8, 0),
		datetime(2026, 8, 1, 18, 0),
		"Capped Actual Time",
	)


def test_auto_verified_capped_time_reduces_pay_for_late_arrival():
	from malaysia_workforce.payroll.pay_engine import select_pay_interval

	start, end, _ = select_pay_interval(
		actual_start=datetime(2026, 8, 1, 8, 30),
		actual_end=datetime(2026, 8, 1, 17, 45),
		scheduled_start=datetime(2026, 8, 1, 8, 0),
		scheduled_end=datetime(2026, 8, 1, 18, 0),
		status="Automatically Verified",
	)
	assert start == datetime(2026, 8, 1, 8, 30)
	assert end == datetime(2026, 8, 1, 17, 45)


def test_breaks_cannot_exceed_worked_interval_and_nonfinite_rate_is_rejected():
	with raises(ValueError, match="cannot exceed"):
		calculate_shift_pay(args(unpaid_break_minutes=500, paid_break_minutes=101))
	with raises(ValueError, match="finite"):
		calculate_shift_pay(args(hourly_rate=Decimal("NaN")))
