from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Iterable


@dataclass(frozen=True)
class EPFCSVRecord:
	member_number: str
	identity_number: str
	name: str
	wages: Decimal
	employer_share: Decimal
	employee_share: Decimal


def _validate(item: EPFCSVRecord) -> None:
	member_number = str(item.member_number or "").strip()
	identity_number = str(item.identity_number or "").strip()
	name = str(item.name or "").strip()
	if not member_number:
		raise ValueError("EPF member number is required")
	if not identity_number:
		raise ValueError("EPF identity number is required")
	if not name:
		raise ValueError("EPF employee name is required")
	for label, value in (("member number", member_number), ("identity number", identity_number), ("name", name)):
		if any(character in value for character in ("\r", "\n", "\x00")):
			raise ValueError(f"EPF {label} contains an unsupported control character")
	for label, value in (
		("wages", item.wages),
		("employer share", item.employer_share),
		("employee share", item.employee_share),
	):
		try:
			amount = Decimal(str(value or 0))
		except (InvalidOperation, TypeError, ValueError) as exc:
			raise ValueError(f"EPF {label} must be numeric") from exc
		if not amount.is_finite():
			raise ValueError(f"EPF {label} must be finite")
		if amount < 0:
			raise ValueError(f"EPF {label} cannot be negative")


def generate_epf_csv(records: Iterable[EPFCSVRecord], *, include_header: bool = True) -> bytes:
	items = tuple(records)
	if not items:
		raise ValueError("EPF contribution file requires at least one employee record")
	stream = io.StringIO(newline="")
	writer = csv.writer(stream, lineterminator="\r\n")
	if include_header:
		writer.writerow(["Member No", "IC No", "Name", "Salary", "EM Share", "EMP Share"])
	for item in items:
		_validate(item)
		writer.writerow(
			[
				item.member_number,
				item.identity_number,
				item.name,
				f"{item.wages:.2f}",
				f"{item.employer_share:.2f}",
				f"{item.employee_share:.2f}",
			]
		)
	return stream.getvalue().encode("utf-8-sig")
