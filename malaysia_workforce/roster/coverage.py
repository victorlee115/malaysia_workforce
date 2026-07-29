from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Iterable


@dataclass(frozen=True)
class TimeWindow:
	start: datetime
	end: datetime
	preference: str = "Available"

	def __post_init__(self):
		if self.end <= self.start:
			raise ValueError("Availability window end must be after start")

	@property
	def hours(self) -> Decimal:
		return Decimal(str((self.end - self.start).total_seconds() / 3600))


@dataclass(frozen=True)
class Requirement:
	start: datetime
	end: datetime
	headcount: int
	role: str = ""
	key: str = ""

	def __post_init__(self):
		if self.end <= self.start:
			raise ValueError("Coverage requirement end must be after start")
		if self.headcount <= 0:
			raise ValueError("Coverage requirement headcount must be positive")


@dataclass(frozen=True)
class Assignment:
	employee: str
	start: datetime
	end: datetime
	role: str = ""

	def __post_init__(self):
		if self.end <= self.start:
			raise ValueError("Assignment end must be after start")


def validate_non_overlapping(windows: Iterable[TimeWindow]) -> tuple[TimeWindow, ...]:
	items = tuple(sorted(windows, key=lambda item: item.start))
	for previous, current in zip(items, items[1:]):
		if current.start < previous.end:
			raise ValueError("Availability windows cannot overlap")
	return items


def window_contains(windows: Iterable[TimeWindow], start: datetime, end: datetime) -> bool:
	return any(window.start <= start and end <= window.end for window in windows)


def slot_points(start: datetime, end: datetime, minutes: int = 30) -> tuple[datetime, ...]:
	if minutes <= 0:
		raise ValueError("Slot minutes must be positive")
	points = []
	cursor = start
	step = timedelta(minutes=minutes)
	while cursor < end:
		points.append(cursor)
		cursor += step
	return tuple(points)


def _role_key(role: str) -> str:
	return (role or "").strip().casefold()


def coverage_grid(
	requirements: Iterable[Requirement], assignments: Iterable[Assignment], *, slot_minutes: int = 30
) -> list[dict]:
	"""Return role-aware, date-aware coverage rows.

	The original implementation treated a multi-day roster as one continuous timeline
	and counted workers from one role against another. This version groups by work date
	and role so an usher can never fill a technical-runner gap and no empty overnight
	slots are generated between roster dates.
	"""
	requirements = tuple(requirements)
	assignments = tuple(assignments)
	if not requirements:
		return []
	groups: dict[tuple[object, str], list[Requirement]] = {}
	for requirement in requirements:
		groups.setdefault((requirement.start.date(), _role_key(requirement.role)), []).append(requirement)

	rows: list[dict] = []
	for (work_date, normalized_role), group in sorted(groups.items(), key=lambda item: (item[0][0], item[0][1])):
		start = min(item.start for item in group)
		end = max(item.end for item in group)
		role = next((item.role for item in group if item.role), "")
		for point in slot_points(start, end, slot_minutes):
			next_point = min(point + timedelta(minutes=slot_minutes), end)
			required = sum(
				item.headcount for item in group if item.start < next_point and point < item.end
			)
			selected = sum(
				1
				for item in assignments
				if item.start.date() == work_date
				and _role_key(item.role) == normalized_role
				and item.start < next_point
				and point < item.end
			)
			if not required and not selected:
				continue
			active_keys = [
				item.key
				for item in group
				if item.key and item.start < next_point and point < item.end
			]
			rows.append(
				{
					"work_date": work_date,
					"role": role,
					"start": point,
					"end": next_point,
					"required": required,
					"selected": selected,
					"gap": max(required - selected, 0),
					"requirement_keys": active_keys,
				}
			)
	return rows


def recommend_assignments(
	*,
	requirement: Requirement,
	candidate_windows: dict[str, tuple[TimeWindow, ...]],
	already_assigned_hours: dict[str, Decimal] | None = None,
	max_hours: dict[str, Decimal] | None = None,
	excluded_employees: set[str] | None = None,
) -> tuple[str, ...]:
	"""Return a transparent, deterministic fair-allocation recommendation.

	Candidates must cover the entire requirement. Those with fewer already assigned
	hours are ranked first, then by preferred availability, then employee ID. The
	manager remains the final decision-maker.
	"""
	already_assigned_hours = already_assigned_hours or {}
	max_hours = max_hours or {}
	excluded_employees = excluded_employees or set()
	duration = Decimal(str((requirement.end - requirement.start).total_seconds() / 3600))
	eligible = []
	for employee, windows in candidate_windows.items():
		if employee in excluded_employees:
			continue
		if not window_contains(windows, requirement.start, requirement.end):
			continue
		allocated = already_assigned_hours.get(employee, Decimal("0"))
		if employee in max_hours and allocated + duration > max_hours[employee]:
			continue
		preferred = any(
			window.preference == "Preferred"
			and window.start <= requirement.start
			and requirement.end <= window.end
			for window in windows
		)
		eligible.append((allocated, 0 if preferred else 1, employee))
	eligible.sort()
	return tuple(item[2] for item in eligible[: requirement.headcount])
