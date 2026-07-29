from __future__ import annotations

import math
from typing import Any

MAX_AVAILABILITY_WINDOWS = 100
MAX_EMPLOYEE_NOTES_LENGTH = 2000
MAX_ROLE_LENGTH = 140
MAX_FLEXIBILITY_MINUTES = 1440

ALLOWED_PREFERENCES = {"Preferred", "Available", "Available if Needed"}
ALLOWED_COMMITMENT_TYPES = {
	"Manager may assign any hours inside my availability",
	"Ask me to confirm exact hours",
}


def optional_positive_float(value: Any, label: str) -> float | None:
	if value in (None, ""):
		return None
	try:
		number = float(value)
	except (TypeError, ValueError) as exc:
		raise ValueError(f"{label} must be a number.") from exc
	if not math.isfinite(number):
		raise ValueError(f"{label} must be a finite number.")
	if number <= 0:
		raise ValueError(f"{label} must be greater than zero.")
	return number


def nonnegative_int(value: Any, label: str, *, maximum: int | None = None) -> int:
	if value in (None, ""):
		return 0
	if isinstance(value, bool):
		number = int(value)
	else:
		try:
			number = int(str(value).strip())
		except (TypeError, ValueError) as exc:
			raise ValueError(f"{label} must be a whole number.") from exc
	if number < 0:
		raise ValueError(f"{label} cannot be negative.")
	if maximum is not None and number > maximum:
		raise ValueError(f"{label} cannot exceed {maximum}.")
	return number


def boolean_flag(value: Any, label: str) -> int:
	if value in (None, "", 0, "0", False, "false", "False"):
		return 0
	if value in (1, "1", True, "true", "True"):
		return 1
	raise ValueError(f"{label} must be true or false.")


def _bounded_text(value: Any, label: str, maximum: int) -> str | None:
	if value in (None, ""):
		return None
	text = str(value).strip()
	if len(text) > maximum:
		raise ValueError(f"{label} cannot exceed {maximum} characters.")
	return text



def validate_preferred_role(value: Any) -> str | None:
	return _bounded_text(value, "Preferred Role", MAX_ROLE_LENGTH)


def validate_application_inputs(
	*,
	minimum_shift_hours: Any,
	maximum_hours: Any,
	split_shifts_allowed: Any,
	commitment_type: Any,
	employee_notes: Any,
) -> dict[str, Any]:
	minimum = optional_positive_float(minimum_shift_hours, "Minimum Shift Hours")
	maximum = optional_positive_float(maximum_hours, "Maximum Hours")
	if minimum is not None and maximum is not None and maximum < minimum:
		raise ValueError("Maximum Hours cannot be below Minimum Shift Hours.")
	commitment = str(commitment_type or "Manager may assign any hours inside my availability").strip()
	if commitment not in ALLOWED_COMMITMENT_TYPES:
		raise ValueError("Confirmation Preference is not valid.")
	return {
		"minimum_shift_hours": minimum,
		"maximum_hours": maximum,
		"split_shifts_allowed": boolean_flag(split_shifts_allowed, "Split Shifts Allowed"),
		"commitment_type": commitment,
		"employee_notes": _bounded_text(employee_notes, "Employee Notes", MAX_EMPLOYEE_NOTES_LENGTH),
	}


def validate_availability_rows(rows: Any) -> list[dict[str, Any]]:
	if not isinstance(rows, list):
		raise ValueError("Availability windows must be a list.")
	if not rows:
		raise ValueError("Add at least one availability window.")
	if len(rows) > MAX_AVAILABILITY_WINDOWS:
		raise ValueError(f"No more than {MAX_AVAILABILITY_WINDOWS} availability windows may be submitted at once.")

	cleaned: list[dict[str, Any]] = []
	for index, row in enumerate(rows, start=1):
		if not isinstance(row, dict):
			raise ValueError(f"Availability window row {index} must be an object.")
		for fieldname, label in (
			("work_date", "Date"),
			("available_from", "Available From"),
			("available_until", "Available Until"),
		):
			if row.get(fieldname) in (None, ""):
				raise ValueError(f"Availability window row {index}: {label} is required.")

		preference = str(row.get("preference") or "Available").strip()
		if preference not in ALLOWED_PREFERENCES:
			raise ValueError(f"Availability window row {index}: Preference is not valid.")
		minimum = optional_positive_float(
			row.get("minimum_assignment_hours"),
			f"Availability window row {index}: Minimum Assignment Hours",
		)
		maximum = optional_positive_float(
			row.get("maximum_assignment_hours"),
			f"Availability window row {index}: Maximum Assignment Hours",
		)
		if minimum is not None and maximum is not None and minimum > maximum:
			raise ValueError(
				f"Availability window row {index}: Minimum Assignment Hours cannot exceed Maximum Assignment Hours."
			)
		cleaned.append(
			{
				"work_date": row.get("work_date"),
				"available_from": row.get("available_from"),
				"available_until": row.get("available_until"),
				"preference": preference,
				"preferred_role": _bounded_text(
					row.get("preferred_role"),
					f"Availability window row {index}: Preferred Role",
					MAX_ROLE_LENGTH,
				),
				"minimum_assignment_hours": minimum,
				"maximum_assignment_hours": maximum,
				"can_start_earlier_minutes": nonnegative_int(
					row.get("can_start_earlier_minutes"),
					f"Availability window row {index}: Can Start Earlier Minutes",
					maximum=MAX_FLEXIBILITY_MINUTES,
				),
				"can_finish_later_minutes": nonnegative_int(
					row.get("can_finish_later_minutes"),
					f"Availability window row {index}: Can Finish Later Minutes",
					maximum=MAX_FLEXIBILITY_MINUTES,
				),
			}
		)
	return cleaned
