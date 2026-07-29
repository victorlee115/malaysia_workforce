from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Iterable


def _finite_decimal(value, label: str) -> Decimal:
	try:
		amount = Decimal(str(value or 0))
	except (InvalidOperation, TypeError, ValueError) as exc:
		raise ValueError(f"{label} must be numeric") from exc
	if not amount.is_finite():
		raise ValueError(f"{label} must be finite")
	return amount


def interval_hours(start: datetime, end: datetime) -> Decimal:
	if end <= start:
		raise ValueError("End must be after start")
	return Decimal(str((end - start).total_seconds())) / Decimal("3600")


def enforce_roster_hour_limits(
	*,
	new_start: datetime,
	new_end: datetime,
	existing_intervals: Iterable[tuple[datetime, datetime]],
	maximum_daily_hours=0,
	maximum_weekly_hours=0,
) -> tuple[Decimal, Decimal]:
	new_hours = interval_hours(new_start, new_end)
	daily_total = new_hours
	weekly_total = new_hours
	for start, end in existing_intervals:
		hours = interval_hours(start, end)
		weekly_total += hours
		if start.date() == new_start.date():
			daily_total += hours
	max_daily = _finite_decimal(maximum_daily_hours, "Maximum daily hours")
	max_weekly = _finite_decimal(maximum_weekly_hours, "Maximum weekly hours")
	if max_daily < 0 or max_weekly < 0:
		raise ValueError("Maximum hours cannot be negative")
	if max_daily > 0 and daily_total > max_daily:
		raise ValueError(
			f"Selection would allocate {daily_total:.2f} hours on the day, above the agreement maximum of {max_daily:.2f}."
		)
	if max_weekly > 0 and weekly_total > max_weekly:
		raise ValueError(
			f"Selection would allocate {weekly_total:.2f} hours in the week, above the agreement maximum of {max_weekly:.2f}."
		)
	return daily_total, weekly_total
