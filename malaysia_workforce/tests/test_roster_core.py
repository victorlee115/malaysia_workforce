from datetime import date, datetime, time, timedelta
from decimal import Decimal

import pytest

from malaysia_workforce.roster.hour_limits import enforce_roster_hour_limits
from malaysia_workforce.roster.input_validation import (
	validate_application_inputs,
	validate_availability_rows,
)
from malaysia_workforce.roster.shift_intervals import assignment_intervals, coerce_time
from malaysia_workforce.roster.shift_policy import canonical_time, dynamic_shift_identity


def test_application_numbers_must_be_finite():
	with pytest.raises(ValueError, match="finite"):
		validate_application_inputs(
			minimum_shift_hours="nan",
			maximum_hours=None,
			split_shifts_allowed=0,
			commitment_type="Manager may assign any hours inside my availability",
			employee_notes=None,
		)
	with pytest.raises(ValueError, match="finite"):
		validate_application_inputs(
			minimum_shift_hours=1,
			maximum_hours="inf",
			split_shifts_allowed=0,
			commitment_type="Manager may assign any hours inside my availability",
			employee_notes=None,
		)


def test_availability_validation_bounds_and_boolean_inputs():
	rows = validate_availability_rows(
		[
			{
				"work_date": "2026-08-01",
				"available_from": "10:00",
				"available_until": "15:00",
				"preference": "Preferred",
				"minimum_assignment_hours": 2,
				"maximum_assignment_hours": 5,
				"can_start_earlier_minutes": 30,
				"can_finish_later_minutes": 15,
			}
		]
	)
	assert rows[0]["minimum_assignment_hours"] == 2.0
	with pytest.raises(ValueError, match="cannot exceed"):
		validate_availability_rows(
			[
				{
					"work_date": "2026-08-01",
					"available_from": "10:00",
					"available_until": "15:00",
					"can_start_earlier_minutes": 1441,
				}
			]
		)


def test_standard_shift_assignments_expand_and_roster_assignments_are_excluded():
	rows = [
		{
			"name": "SHIFT-1",
			"employee": "EMP-1",
			"shift_type": "Night",
			"start_date": date(2026, 8, 1),
			"end_date": date(2026, 8, 2),
			"custom_roster_selection": None,
		},
		{
			"name": "SHIFT-ROSTER",
			"employee": "EMP-1",
			"shift_type": "Night",
			"start_date": date(2026, 8, 1),
			"end_date": date(2026, 8, 1),
			"custom_roster_selection": "MW-SEL-1",
		},
	]
	result = assignment_intervals(
		rows,
		shift_times={"Night": (time(22, 0), timedelta(hours=6))},
		range_start=date(2026, 8, 1),
		range_end=date(2026, 8, 2),
	)
	assert len(result) == 2
	assert result[0]["start"] == datetime(2026, 8, 1, 22, 0)
	assert result[0]["end"] == datetime(2026, 8, 2, 6, 0)
	assert {row["name"] for row in result} == {"SHIFT-1"}


def test_custom_shift_interval_and_datetime_dates():
	result = assignment_intervals(
		[
			{
				"name": "SHIFT-CUSTOM",
				"employee": "EMP-1",
				"start_date": datetime(2026, 8, 1, 0, 0),
				"end_date": datetime(2026, 8, 1, 0, 0),
				"custom_assigned_start_datetime": "2026-08-01T09:00:00",
				"custom_assigned_end_datetime": "2026-08-01T13:00:00",
			}
		],
		shift_times={},
		range_start=date(2026, 8, 1),
		range_end=date(2026, 8, 1),
	)
	assert result[0]["end"] - result[0]["start"] == timedelta(hours=4)


def test_hour_limits_include_existing_daily_and_weekly_work():
	start = datetime(2026, 8, 3, 12, 0)
	end = datetime(2026, 8, 3, 16, 0)
	existing = [(datetime(2026, 8, 3, 8, 0), datetime(2026, 8, 3, 12, 0))]
	assert enforce_roster_hour_limits(
		new_start=start,
		new_end=end,
		existing_intervals=existing,
		maximum_daily_hours=8,
		maximum_weekly_hours=45,
	) == (Decimal("8"), Decimal("8"))
	with pytest.raises(ValueError, match="above the agreement maximum"):
		enforce_roster_hour_limits(
			new_start=start,
			new_end=end + timedelta(hours=1),
			existing_intervals=existing,
			maximum_daily_hours=8,
			maximum_weekly_hours=45,
		)
	with pytest.raises(ValueError, match="finite"):
		enforce_roster_hour_limits(
			new_start=start,
			new_end=end,
			existing_intervals=(),
			maximum_daily_hours="nan",
		)


def test_dynamic_shift_identity_is_stable_and_policy_specific():
	name1, fingerprint1 = dynamic_shift_identity("09:00", "17:00")
	name2, fingerprint2 = dynamic_shift_identity(time(9, 0), timedelta(hours=17))
	assert name1 == name2
	assert fingerprint1 == fingerprint2
	assert name1.startswith("MW-AUTO-0900-1700-")
	assert canonical_time("9:05") == "09:05:00"
	assert coerce_time(timedelta(hours=25, minutes=30)) == time(1, 30)
