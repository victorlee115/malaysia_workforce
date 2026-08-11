from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Iterable

ALLOCATOR_VERSION = "MW-STAFF-2026.1"


@dataclass(frozen=True)
class Interval:
	start: datetime
	end: datetime

	def __post_init__(self):
		if self.end <= self.start:
			raise ValueError("Interval end must be after start")

	@property
	def minutes(self) -> int:
		return int((self.end - self.start).total_seconds() // 60)


@dataclass(frozen=True)
class Demand:
	key: str
	work_date: date
	start: datetime
	end: datetime
	headcount: int
	designation: str = ""
	required_skill: str = ""
	critical: bool = False

	def __post_init__(self):
		if self.end <= self.start:
			raise ValueError("Demand end must be after start")
		if self.start.date() != self.work_date:
			raise ValueError("Demand start must fall on work_date")
		if self.headcount < 1:
			raise ValueError("Demand headcount must be positive")


@dataclass(frozen=True)
class Worker:
	employee: str
	availability: tuple[Interval, ...]
	designation: str = ""
	skills: frozenset[str] = field(default_factory=frozenset)
	priority: str = "Standard"
	projected_hours: float = 0
	submitted_on: datetime | None = None
	maximum_daily_hours: float = 12
	maximum_weekly_hours: float = 45
	minimum_shift_hours: float = 2
	split_shifts_allowed: bool = False
	existing_intervals: tuple[Interval, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Assignment:
	key: str
	requirement_key: str
	employee: str
	start: datetime
	end: datetime
	priority: str

	@property
	def hours(self) -> float:
		return (self.end - self.start).total_seconds() / 3600


@dataclass(frozen=True)
class Gap:
	requirement_key: str
	start: datetime
	end: datetime
	missing_headcount: int
	critical: bool


@dataclass(frozen=True)
class AllocationResult:
	assignments: tuple[Assignment, ...]
	gaps: tuple[Gap, ...]
	covered_minutes: int
	required_minutes: int

	@property
	def coverage_percent(self) -> float:
		if not self.required_minutes:
			return 100.0
		return round(self.covered_minutes / self.required_minutes * 100, 2)


def _overlaps(left: Interval, right: Interval) -> bool:
	return left.start < right.end and right.start < left.end


def _week_start(value: date) -> date:
	return value - timedelta(days=value.weekday())


def _priority_rank(value: str) -> int:
	return {"Priority": 0, "Preferred": 1, "Standard": 2}.get(value or "Standard", 2)


def _eligible(worker: Worker, demand: Demand) -> bool:
	if demand.designation and worker.designation != demand.designation:
		return False
	if demand.required_skill and demand.required_skill not in worker.skills:
		return False
	return True


def _availability_intersections(worker: Worker, demand: Demand) -> Iterable[Interval]:
	for window in worker.availability:
		start = max(window.start, demand.start)
		end = min(window.end, demand.end)
		if end > start:
			yield Interval(start, end)


def _slot_starts(start: datetime, end: datetime, slot_minutes: int) -> list[datetime]:
	step = timedelta(minutes=slot_minutes)
	result = []
	cursor = start
	while cursor + step <= end:
		result.append(cursor)
		cursor += step
	return result


def _longest_uncovered_segment(
	interval: Interval,
	remaining: dict[datetime, int],
	*,
	slot_minutes: int,
	maximum_minutes: int,
) -> Interval | None:
	step = timedelta(minutes=slot_minutes)
	best: tuple[datetime, datetime] | None = None
	segment_start: datetime | None = None
	previous: datetime | None = None
	for slot in _slot_starts(interval.start, interval.end, slot_minutes):
		if remaining.get(slot, 0) > 0:
			if segment_start is None or (previous and slot != previous + step):
				segment_start = slot
			previous = slot
			segment_end = slot + step
			if best is None or segment_end - segment_start > best[1] - best[0]:
				best = (segment_start, segment_end)
		else:
			segment_start = None
			previous = None
	if not best:
		return None
	start, end = best
	if int((end - start).total_seconds() // 60) > maximum_minutes:
		end = start + timedelta(minutes=maximum_minutes)
	return Interval(start, end)


def _hours_on_day(intervals: Iterable[Interval], day: date) -> float:
	return sum(item.minutes for item in intervals if item.start.date() == day) / 60


def _hours_in_week(intervals: Iterable[Interval], day: date) -> float:
	week = _week_start(day)
	return sum(item.minutes for item in intervals if _week_start(item.start.date()) == week) / 60


def _within_hours(worker: Worker, proposed: Interval, assigned: list[Assignment]) -> bool:
	intervals = list(worker.existing_intervals)
	intervals.extend(
		Interval(row.start, row.end) for row in assigned if row.employee == worker.employee
	)
	daily = _hours_on_day(intervals, proposed.start.date()) + proposed.minutes / 60
	weekly = _hours_in_week(intervals, proposed.start.date()) + proposed.minutes / 60
	return (
		(not worker.maximum_daily_hours or daily <= worker.maximum_daily_hours)
		and (not worker.maximum_weekly_hours or weekly <= worker.maximum_weekly_hours)
	)


def _has_conflict(worker: Worker, proposed: Interval, assigned: list[Assignment]) -> bool:
	if any(_overlaps(proposed, existing) for existing in worker.existing_intervals):
		return True
	worker_intervals = list(worker.existing_intervals)
	worker_intervals.extend(
		Interval(row.start, row.end) for row in assigned if row.employee == worker.employee
	)
	if any(_overlaps(proposed, existing) for existing in worker_intervals):
		return True
	if worker.split_shifts_allowed:
		return False
	return any(
		existing.start.date() == proposed.start.date()
		and proposed.end != existing.start
		and proposed.start != existing.end
		for existing in worker_intervals
	)


def allocate_staff(
	demands: Iterable[Demand],
	workers: Iterable[Worker],
	*,
	slot_minutes: int = 30,
	preferred_minimum_hours: float = 4,
	normal_minimum_hours: float = 2,
	maximum_assignment_hours: float = 8,
) -> AllocationResult:
	"""Allocate longer useful spans before priority and fairness.

	The engine intentionally leaves short gaps unfilled. One-hour emergency shifts
	are a documented manager override, never an automatic recommendation.
	"""
	if slot_minutes <= 0 or 60 % slot_minutes:
		raise ValueError("slot_minutes must be a positive divisor of 60")
	if not 0 < normal_minimum_hours <= preferred_minimum_hours <= maximum_assignment_hours:
		raise ValueError("Invalid assignment-length policy")

	demand_rows = sorted(
		demands,
		key=lambda row: (not row.critical, row.work_date, row.start, row.end, row.key),
	)
	worker_rows = sorted(workers, key=lambda row: row.employee)
	remaining = {
		row.key: {slot: row.headcount for slot in _slot_starts(row.start, row.end, slot_minutes)}
		for row in demand_rows
	}
	assignments: list[Assignment] = []
	sequence = 0

	for minimum_hours in (preferred_minimum_hours, normal_minimum_hours):
		minimum_minutes = int(minimum_hours * 60)
		while True:
			candidates = []
			for demand in demand_rows:
				for worker in worker_rows:
					if not _eligible(worker, demand):
						continue
					for available in _availability_intersections(worker, demand):
						span = _longest_uncovered_segment(
							available,
							remaining[demand.key],
							slot_minutes=slot_minutes,
							maximum_minutes=int(maximum_assignment_hours * 60),
						)
						worker_minimum = max(minimum_minutes, int(worker.minimum_shift_hours * 60))
						if not span or span.minutes < worker_minimum:
							continue
						if _has_conflict(worker, span, assignments) or not _within_hours(worker, span, assignments):
							continue
						already_assigned = sum(
							row.hours for row in assignments if row.employee == worker.employee
						)
						submitted = worker.submitted_on or datetime.max
						candidates.append(
							(
								0 if demand.critical else 1,
								-span.minutes,
								_priority_rank(worker.priority),
								worker.projected_hours + already_assigned,
								submitted,
								worker.employee,
								demand.key,
								span,
								worker,
							)
						)
			if not candidates:
				break
			*_, demand_key, span, worker = min(candidates)
			sequence += 1
			assignment = Assignment(
				key=f"{demand_key}:{worker.employee}:{span.start.isoformat()}:{sequence}",
				requirement_key=demand_key,
				employee=worker.employee,
				start=span.start,
				end=span.end,
				priority=worker.priority,
			)
			assignments.append(assignment)
			for slot in _slot_starts(span.start, span.end, slot_minutes):
				if slot in remaining[demand_key]:
					remaining[demand_key][slot] = max(remaining[demand_key][slot] - 1, 0)

	gaps: list[Gap] = []
	required_minutes = 0
	uncovered_minutes = 0
	step = timedelta(minutes=slot_minutes)
	for demand in demand_rows:
		required_minutes += demand.headcount * int((demand.end - demand.start).total_seconds() // 60)
		slots = remaining[demand.key]
		for missing in range(1, demand.headcount + 1):
			segment_start = None
			previous = None
			for slot in _slot_starts(demand.start, demand.end, slot_minutes) + [demand.end]:
				is_missing = slot != demand.end and slots.get(slot, 0) >= missing
				if is_missing and segment_start is None:
					segment_start = slot
				if segment_start is not None and (not is_missing or (previous and slot != previous + step)):
					end = previous + step if previous else slot
					gaps.append(Gap(demand.key, segment_start, end, 1, demand.critical))
					uncovered_minutes += int((end - segment_start).total_seconds() // 60)
					segment_start = slot if is_missing else None
				previous = slot if is_missing else None
	return AllocationResult(
		assignments=tuple(sorted(assignments, key=lambda row: (row.start, row.employee, row.key))),
		gaps=tuple(gaps),
		covered_minutes=required_minutes - uncovered_minutes,
		required_minutes=required_minutes,
	)
