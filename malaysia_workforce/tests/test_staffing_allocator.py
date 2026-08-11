from datetime import date, datetime, time, timedelta

from malaysia_workforce.staffing.allocator import Demand, Interval, Worker, allocate_staff
from malaysia_workforce.staffing.intervals import assignment_intervals, coerce_time
from malaysia_workforce.staffing.shift_identity import managed_shift_identity


DAY = date(2026, 9, 7)


def dt(hour, minute=0):
	return datetime.combine(DAY, time(hour, minute))


def worker(employee, start, end, *, priority="Standard", hours=0, skills=(), designation="Barista"):
	return Worker(
		employee=employee,
		availability=(Interval(dt(start), dt(end)),),
		designation=designation,
		skills=frozenset(skills),
		priority=priority,
		projected_hours=hours,
		submitted_on=datetime(2026, 8, 20, 9),
	)


def demand(start=9, end=17, *, headcount=1, critical=True, skill=""):
	return Demand("REQ-1", DAY, dt(start), dt(end), headcount, "Barista", skill, critical)


def test_long_continuous_coverage_beats_priority_fragment():
	result = allocate_staff(
		[demand()],
		[
			worker("EMP-PRIORITY", 9, 12, priority="Priority"),
			worker("EMP-LONG", 9, 15, priority="Standard"),
		],
	)
	assert result.assignments[0].employee == "EMP-LONG"
	assert result.assignments[0].hours == 6


def test_priority_then_fewer_hours_breaks_equal_length_ties():
	result = allocate_staff(
		[demand(9, 13)],
		[
			worker("EMP-PREFERRED", 9, 13, priority="Preferred", hours=20),
			worker("EMP-STANDARD", 9, 13, priority="Standard", hours=0),
		],
	)
	assert result.assignments[0].employee == "EMP-PREFERRED"
	result = allocate_staff(
		[demand(9, 13)],
		[
			worker("EMP-A", 9, 13, hours=20),
			worker("EMP-B", 9, 13, hours=4),
		],
	)
	assert result.assignments[0].employee == "EMP-B"


def test_one_hour_gap_is_visible_and_never_auto_allocated():
	result = allocate_staff([demand(9, 10)], [worker("EMP-1", 9, 10)])
	assert not result.assignments
	assert result.gaps[0].start == dt(9)
	assert result.gaps[0].end == dt(10)
	assert result.coverage_percent == 0


def test_two_hour_fallback_and_skill_gate_are_deterministic():
	workers = [
		worker("EMP-2", 9, 12, skills=()),
		worker("EMP-1", 9, 12, skills=("Coffee",)),
	]
	first = allocate_staff([demand(9, 12, skill="Coffee")], workers)
	second = allocate_staff([demand(9, 12, skill="Coffee")], reversed(workers))
	assert first == second
	assert first.assignments[0].employee == "EMP-1"
	assert first.assignments[0].hours == 3


def test_existing_conflict_and_hour_limits_leave_shortage():
	busy = Worker(
		employee="EMP-1",
		availability=(Interval(dt(9), dt(17)),),
		designation="Barista",
		existing_intervals=(Interval(dt(8), dt(12)),),
		maximum_daily_hours=8,
	)
	result = allocate_staff([demand()], [busy])
	assert not result.assignments
	assert result.required_minutes == 480


def test_effective_agreement_minimum_is_never_bypassed():
	strict = Worker(
		employee="EMP-1",
		availability=(Interval(dt(9), dt(12)),),
		designation="Barista",
		minimum_shift_hours=4,
	)
	result = allocate_staff([demand(9, 12)], [strict])
	assert not result.assignments
	assert result.coverage_percent == 0


def test_split_shift_is_rejected_unless_agreement_allows_it():
	first = Demand("REQ-AM", DAY, dt(9), dt(13), 1, "Barista", "", True)
	second = Demand("REQ-PM", DAY, dt(15), dt(19), 1, "Barista", "", True)
	no_split = Worker(
		employee="EMP-1",
		availability=(Interval(dt(9), dt(19)),),
		designation="Barista",
		split_shifts_allowed=False,
	)
	result = allocate_staff([first, second], [no_split])
	assert len(result.assignments) == 1
	assert result.gaps
	with_split = Worker(
		employee="EMP-1",
		availability=(Interval(dt(9), dt(19)),),
		designation="Barista",
		split_shifts_allowed=True,
	)
	assert len(allocate_staff([first, second], [with_split]).assignments) == 2


def test_standard_shift_assignments_expand_overnight_without_custom_times():
	rows = [{"name": "SHIFT-1", "employee": "EMP-1", "shift_type": "Night", "start_date": DAY, "end_date": DAY}]
	result = assignment_intervals(rows, shift_times={"Night": (time(22), timedelta(hours=6))}, range_start=DAY, range_end=DAY)
	assert result[0]["start"] == datetime(2026, 9, 7, 22)
	assert result[0]["end"] == datetime(2026, 9, 8, 6)
	assert coerce_time(timedelta(hours=25, minutes=30)) == time(1, 30)


def test_managed_shift_identity_reuses_exact_template_and_times():
	first = managed_shift_identity("Casual Base", "09:00", "17:00")
	second = managed_shift_identity("Casual Base", time(9), timedelta(hours=17))
	assert first == second
	assert first[0].startswith("MW Flexible 0900-1700-")
