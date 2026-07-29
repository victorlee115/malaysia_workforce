from __future__ import annotations

import hashlib
import json
from datetime import time, timedelta

DYNAMIC_SHIFT_POLICY = {
	"enable_auto_attendance": 0,
	"determine_check_in_and_check_out": "Strictly based on Log Type in Employee Checkin",
	"working_hours_calculation_based_on": "First Check-in and Last Check-out",
}


def canonical_time(value) -> str:
	"""Return a stable ``HH:MM:SS`` representation for Frappe Time values."""
	if isinstance(value, timedelta):
		seconds = int(value.total_seconds()) % (24 * 60 * 60)
		hour, remainder = divmod(seconds, 3600)
		minute, second = divmod(remainder, 60)
		return f"{hour:02d}:{minute:02d}:{second:02d}"
	if isinstance(value, time):
		return value.strftime("%H:%M:%S")
	if hasattr(value, "strftime"):
		return value.strftime("%H:%M:%S")
	text = str(value or "").strip()
	parts = text.split(":")
	if len(parts) not in {2, 3}:
		raise ValueError(f"Invalid shift time: {value!r}")
	try:
		hour, minute = int(parts[0]), int(parts[1])
		second = int(float(parts[2])) if len(parts) == 3 else 0
	except (TypeError, ValueError) as exc:
		raise ValueError(f"Invalid shift time: {value!r}") from exc
	if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
		raise ValueError(f"Invalid shift time: {value!r}")
	return f"{hour:02d}:{minute:02d}:{second:02d}"


def dynamic_shift_identity(start_time, end_time) -> tuple[str, str]:
	payload = {
		"start_time": canonical_time(start_time),
		"end_time": canonical_time(end_time),
		**DYNAMIC_SHIFT_POLICY,
	}
	fingerprint = hashlib.sha256(
		json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
	).hexdigest()
	compact_start = payload["start_time"].replace(":", "")[:4]
	compact_end = payload["end_time"].replace(":", "")[:4]
	return f"MW-AUTO-{compact_start}-{compact_end}-{fingerprint[:8]}", fingerprint
