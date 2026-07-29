from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from malaysia_workforce.statutory.common import ZERO, decimal

PAY_ENGINE_VERSION = "MW-PAY-2026.2"
AUTO_VERIFIED_PAY_POLICIES = {
	"Capped Actual Time",
	"Scheduled Time",
	"Actual Time",
}
CENT = Decimal("0.01")
HOUR_QUANTUM = Decimal("0.0001")
HOUR = Decimal("3600")
MINUTE = Decimal("60")


@dataclass(frozen=True)
class PayRule:
	ordinary_multiplier: Decimal = Decimal("1")
	additional_multiplier: Decimal = Decimal("1")
	overtime_multiplier: Decimal = Decimal("1.5")
	rest_normal_multiplier: Decimal = Decimal("2")
	rest_additional_multiplier: Decimal = Decimal("1.5")
	rest_overtime_multiplier: Decimal = Decimal("2")
	public_holiday_normal_multiplier: Decimal = Decimal("3")
	public_holiday_additional_multiplier: Decimal = Decimal("2")
	public_holiday_overtime_multiplier: Decimal = Decimal("3")


@dataclass(frozen=True)
class ShiftPayInput:
	actual_start: datetime
	actual_end: datetime
	hourly_rate: Decimal
	unpaid_break_minutes: int = 0
	paid_break_minutes: int = 0
	normal_part_time_daily_hours: Decimal = ZERO
	comparable_full_time_daily_hours: Decimal = Decimal("8")
	is_rest_day: bool = False
	is_public_holiday: bool = False


@dataclass(frozen=True)
class PayLine:
	component: str
	hours: Decimal
	rate: Decimal
	multiplier: Decimal
	amount: Decimal
	explanation: str

	def to_dict(self) -> dict[str, Any]:
		data = asdict(self)
		for key in ("hours", "rate", "multiplier", "amount"):
			data[key] = str(data[key])
		return data


@dataclass(frozen=True)
class ShiftPayResult:
	payable_hours: Decimal
	ordinary_hours: Decimal
	additional_hours: Decimal
	overtime_hours: Decimal
	gross_pay: Decimal
	lines: tuple[PayLine, ...]
	version: str = PAY_ENGINE_VERSION

	def to_dict(self) -> dict[str, Any]:
		return {
			"payable_hours": str(self.payable_hours),
			"ordinary_hours": str(self.ordinary_hours),
			"additional_hours": str(self.additional_hours),
			"overtime_hours": str(self.overtime_hours),
			"gross_pay": str(self.gross_pay),
			"lines": [line.to_dict() for line in self.lines],
			"version": self.version,
		}


def pay_money(value) -> Decimal:
	return decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def select_pay_interval(
	*,
	actual_start: datetime,
	actual_end: datetime,
	scheduled_start: datetime,
	scheduled_end: datetime,
	status: str,
	auto_verified_policy: str = "Capped Actual Time",
) -> tuple[datetime, datetime, str]:
	"""Choose the interval that may generate pay.

	Manager-approved records use their actual interval. Automatically verified records
	default to a capped interval: late arrival or early departure reduces payable time,
	while unapproved early arrival or late departure does not increase it.
	"""
	if actual_end <= actual_start:
		raise ValueError("Actual end must be after actual start")
	if scheduled_end <= scheduled_start:
		raise ValueError("Scheduled end must be after scheduled start")
	if status != "Automatically Verified":
		return actual_start, actual_end, "Actual Time"
	if auto_verified_policy not in AUTO_VERIFIED_PAY_POLICIES:
		raise ValueError(f"Unsupported auto-verified pay policy: {auto_verified_policy}")
	if auto_verified_policy == "Actual Time":
		return actual_start, actual_end, auto_verified_policy
	if auto_verified_policy == "Scheduled Time":
		return scheduled_start, scheduled_end, auto_verified_policy
	effective_start = max(actual_start, scheduled_start)
	effective_end = min(actual_end, scheduled_end)
	if effective_end <= effective_start:
		raise ValueError("Actual attendance does not overlap the scheduled shift")
	return effective_start, effective_end, auto_verified_policy


def _quantized_hours(seconds: Decimal) -> Decimal:
	return (seconds / HOUR).quantize(HOUR_QUANTUM, rounding=ROUND_HALF_UP)


def calculate_shift_pay(args: ShiftPayInput, rule: PayRule | None = None) -> ShiftPayResult:
	rule = rule or PayRule()
	if args.actual_end <= args.actual_start:
		raise ValueError("Actual end must be after actual start")
	if args.unpaid_break_minutes < 0 or args.paid_break_minutes < 0:
		raise ValueError("Break minutes cannot be negative")
	rate = decimal(args.hourly_rate)
	if rate <= ZERO:
		raise ValueError("Hourly rate must be greater than zero")
	normal_limit = decimal(args.normal_part_time_daily_hours)
	full_time_limit = decimal(args.comparable_full_time_daily_hours)
	if normal_limit < ZERO or full_time_limit < ZERO:
		raise ValueError("Daily hour limits cannot be negative")

	worked_seconds = Decimal(str((args.actual_end - args.actual_start).total_seconds()))
	unpaid_seconds = Decimal(args.unpaid_break_minutes) * MINUTE
	paid_seconds = Decimal(args.paid_break_minutes) * MINUTE
	if unpaid_seconds + paid_seconds > worked_seconds:
		raise ValueError("Paid and unpaid breaks cannot exceed the worked interval")
	payable = _quantized_hours(worked_seconds - unpaid_seconds)
	if normal_limit <= ZERO:
		normal_limit = payable
	if full_time_limit <= ZERO:
		full_time_limit = normal_limit
	full_time_limit = max(full_time_limit, normal_limit)
	ordinary = min(payable, normal_limit).quantize(HOUR_QUANTUM, rounding=ROUND_HALF_UP)
	additional = min(max(payable - ordinary, ZERO), max(full_time_limit - normal_limit, ZERO)).quantize(
		HOUR_QUANTUM, rounding=ROUND_HALF_UP
	)
	overtime = max(payable - ordinary - additional, ZERO).quantize(HOUR_QUANTUM, rounding=ROUND_HALF_UP)

	if args.is_public_holiday:
		multipliers = (
			rule.public_holiday_normal_multiplier,
			rule.public_holiday_additional_multiplier,
			rule.public_holiday_overtime_multiplier,
		)
		components = ("Public Holiday Pay", "Public Holiday Pay", "Public Holiday Pay")
		reasons = (
			"Public-holiday normal hours",
			"Public-holiday hours above part-time normal hours",
			"Public-holiday hours above comparable full-time hours",
		)
	elif args.is_rest_day:
		multipliers = (
			rule.rest_normal_multiplier,
			rule.rest_additional_multiplier,
			rule.rest_overtime_multiplier,
		)
		components = ("Rest Day Pay", "Rest Day Pay", "Rest Day Pay")
		reasons = (
			"Rest-day normal hours",
			"Rest-day hours above part-time normal hours",
			"Rest-day hours above comparable full-time hours",
		)
	else:
		multipliers = (rule.ordinary_multiplier, rule.additional_multiplier, rule.overtime_multiplier)
		components = ("Casual Ordinary Pay", "Part-Time Additional Hours", "Casual Overtime Pay")
		reasons = (
			"Ordinary hours",
			"Hours above part-time normal hours up to comparable full-time hours",
			"Hours above comparable full-time hours",
		)

	lines = []
	for component, hours, multiplier, reason in zip(
		components,
		(ordinary, additional, overtime),
		multipliers,
		reasons,
	):
		if hours <= ZERO:
			continue
		amount = pay_money(hours * rate * decimal(multiplier))
		lines.append(PayLine(component, hours, pay_money(rate), decimal(multiplier), amount, reason))
	return ShiftPayResult(
		payable_hours=payable,
		ordinary_hours=ordinary,
		additional_hours=additional,
		overtime_hours=overtime,
		gross_pay=pay_money(sum((line.amount for line in lines), ZERO)),
		lines=tuple(lines),
	)
