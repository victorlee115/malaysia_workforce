from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date, datetime, time, timedelta
from typing import Any


def coerce_time(value: Any) -> time:
	"""Convert Frappe/MariaDB Time values to ``datetime.time``.

	Frappe can expose a Time field as ``datetime.time``, ``datetime.timedelta`` or
	a string depending on the database driver and call site.
	"""
	if isinstance(value, time):
		return value
	if isinstance(value, datetime):
		return value.time()
	if isinstance(value, timedelta):
		seconds = int(value.total_seconds()) % 86400
		return time(seconds // 3600, (seconds % 3600) // 60, seconds % 60)
	if isinstance(value, str):
		text = value.strip()
		parts = text.split(":")
		if len(parts) not in {2, 3}:
			raise ValueError(f"Invalid time value: {value!r}")
		hour, minute = int(parts[0]), int(parts[1])
		second = int(float(parts[2])) if len(parts) == 3 else 0
		return time(hour, minute, second)
	raise ValueError(f"Invalid time value: {value!r}")


def assignment_intervals(
	rows: Iterable[Mapping[str, Any]],
	*,
	shift_times: Mapping[str, tuple[Any, Any]],
	range_start: date,
	range_end: date,
) -> tuple[dict[str, Any], ...]:
	"""Expand standard Frappe HR Shift Assignments into concrete intervals.

	Roster-managed Shift Assignments are intentionally excluded because their source
	Roster Selections are evaluated separately. This prevents double-counting hours.
	"""
	if range_end < range_start:
		raise ValueError("range_end cannot be before range_start")

	intervals: list[dict[str, Any]] = []
	for row in rows:
		if row.get("custom_roster_selection"):
			continue
		name = row.get("name")
		employee = row.get("employee")
		custom_start = row.get("custom_assigned_start_datetime")
		custom_end = row.get("custom_assigned_end_datetime")
		if custom_start and custom_end:
			start = custom_start if isinstance(custom_start, datetime) else datetime.fromisoformat(str(custom_start))
			end = custom_end if isinstance(custom_end, datetime) else datetime.fromisoformat(str(custom_end))
			if end <= start:
				raise ValueError(f"Shift Assignment {name} has an invalid custom interval")
			if start.date() <= range_end and end.date() >= range_start:
				intervals.append({"name": name, "employee": employee, "start": start, "end": end})
			continue

		row_start = row.get("start_date")
		if not row_start:
			continue
		if isinstance(row_start, datetime):
			row_start = row_start.date()
		elif not isinstance(row_start, date):
			row_start = date.fromisoformat(str(row_start))
		row_end = row.get("end_date") or row_start
		if isinstance(row_end, datetime):
			row_end = row_end.date()
		elif not isinstance(row_end, date):
			row_end = date.fromisoformat(str(row_end))
		first_day = max(row_start, range_start)
		last_day = min(row_end, range_end)
		if first_day > last_day:
			continue
		shift_type = row.get("shift_type")
		if not shift_type or shift_type not in shift_times:
			raise ValueError(f"Shift Assignment {name} has no usable Shift Type timing")
		start_time, end_time = shift_times[shift_type]
		start_time = coerce_time(start_time)
		end_time = coerce_time(end_time)
		day = first_day
		while day <= last_day:
			start = datetime.combine(day, start_time)
			end = datetime.combine(day, end_time)
			if end <= start:
				end += timedelta(days=1)
			intervals.append({"name": name, "employee": employee, "start": start, "end": end})
			day += timedelta(days=1)
	return tuple(intervals)
