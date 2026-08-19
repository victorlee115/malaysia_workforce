from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Iterable

from malaysia_workforce.statutory.exporters.common import digits


@dataclass(frozen=True)
class EPFCSVRecord:
	member_number: str
	identity_number: str
	name: str
	wages: Decimal
	employer_share: Decimal
	employee_share: Decimal


def _ascii_text(value, label: str) -> str:
	text = "" if value is None else str(value)
	try:
		text.encode("ascii")
	except UnicodeEncodeError as exc:
		raise ValueError(f"{label} contains non-ASCII characters; provide the authority-approved ASCII spelling") from exc
	if any(character in text for character in ("\r", "\n", "\x00")):
		raise ValueError(f"{label} contains an unsupported control character")
	return text


def _normalized_identity(item: EPFCSVRecord) -> tuple[str, str, str]:
	member_number = digits(item.member_number)
	identity_number = digits(item.identity_number)
	name = _ascii_text(item.name, "EPF employee name").strip()
	if not member_number:
		raise ValueError("EPF member number is required")
	if not identity_number:
		raise ValueError("EPF identity number is required")
	if not name:
		raise ValueError("EPF employee name is required")
	return member_number, identity_number, name


def _validate_amounts(item: EPFCSVRecord) -> None:
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
		writer.writerow(["Member No", "IC No", "Name", "Salary", "Employer Share", "Employee Share"])
	for item in items:
		_validate_amounts(item)
		member_number, identity_number, name = _normalized_identity(item)
		writer.writerow(
			[
				member_number,
				identity_number,
				name,
				f"{item.wages:.2f}",
				f"{item.employer_share:.2f}",
				f"{item.employee_share:.2f}",
			]
		)
	return stream.getvalue().encode("utf-8-sig")
