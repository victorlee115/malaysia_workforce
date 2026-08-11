from __future__ import annotations

import hashlib

from malaysia_workforce.staffing.intervals import coerce_time


def managed_shift_identity(template: str, start_time, end_time) -> tuple[str, str]:
	start = coerce_time(start_time).strftime("%H:%M:%S")
	end = coerce_time(end_time).strftime("%H:%M:%S")
	payload = f"{template}|{start}|{end}"
	fingerprint = hashlib.sha256(payload.encode()).hexdigest()
	name = f"MW Flexible {start[:5].replace(':', '')}-{end[:5].replace(':', '')}-{fingerprint[:8]}"
	return name, fingerprint
