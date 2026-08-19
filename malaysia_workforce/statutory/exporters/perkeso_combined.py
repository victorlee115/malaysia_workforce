from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from malaysia_workforce.statutory.exporters.common import assert_length, cents, digits, fixed_text

RECORD_LENGTH = 278


@dataclass(frozen=True)
class PERKESOCombinedRecord:
	employer_code: str
	company_registration_number: str
	employee_identity_number: str
	employee_name: str
	contribution_month: str  # MMYYYY
	wages: Decimal
	socso_employer: Decimal
	socso_employee: Decimal
	eis_employer: Decimal
	eis_employee: Decimal
	skbbk_employee: Decimal


def _max_text(value: str, length: int, label: str, *, required: bool = False) -> str:
	text = "" if value is None else str(value)
	try:
		text.encode("ascii")
	except UnicodeEncodeError as exc:
		raise ValueError(f"{label} contains non-ASCII characters; provide the authority-approved ASCII spelling") from exc
	if any(character in text for character in ("\r", "\n", "\x00")):
		raise ValueError(f"{label} contains an unsupported control character")
	if required and not text.strip():
		raise ValueError(f"{label} is required")
	if len(text) > length:
		raise ValueError(f"{label} exceeds the {length}-character PERKESO field")
	return text


def render_record(item: PERKESOCombinedRecord) -> str:
	month = digits(item.contribution_month)
	if len(month) != 6 or not 1 <= int(month[:2]) <= 12:
		raise ValueError("PERKESO contribution_month must be valid MMYYYY")
	if int(month[2:]) < 2000:
		raise ValueError("PERKESO contribution year must be 2000 or later")
	for label, amount in (
		("wages", item.wages),
		("SOCSO employer", item.socso_employer),
		("SOCSO employee", item.socso_employee),
		("EIS employer", item.eis_employer),
		("EIS employee", item.eis_employee),
		("SKBBK employee", item.skbbk_employee),
	):
		if Decimal(str(amount or 0)) < 0:
			raise ValueError(f"PERKESO {label} amount cannot be negative")
	record = "".join(
		(
			fixed_text(_max_text(item.employer_code, 12, "Employer code", required=True), 12, uppercase=True),
			# MyCoID/SSM Number is field 2 (position 13-32) in PERKESO's own "Spesifikasi
			# Format Text File Untuk SOCSO + EIS Contribution" v1.0 (22 July 2022), marked
			# Mandatory: N ("ROB, ROC") — genuinely optional, not a gap to close.
			fixed_text(_max_text(item.company_registration_number, 20, "Company registration number"), 20, uppercase=True),
			fixed_text(_max_text(digits(item.employee_identity_number), 12, "Employee identification number", required=True), 12, uppercase=True),
			fixed_text(_max_text(item.employee_name, 150, "Employee name", required=True), 150, uppercase=True),
			month,
			cents(item.wages, 14),
			cents(item.socso_employer, 6),
			cents(item.socso_employee, 6),
			cents(item.eis_employer, 6),
			cents(item.eis_employee, 6),
			cents(item.skbbk_employee, 6),
			" " * 14,
			" " * 20,
		)
	)
	return assert_length(record, RECORD_LENGTH, "PERKESO combined contribution record")


def generate_perkeso_combined_file(records: Iterable[PERKESOCombinedRecord]) -> bytes:
	items = tuple(records)
	if not items:
		raise ValueError("PERKESO contribution file requires at least one employee record")
	return ("\r\n".join(render_record(item) for item in items) + "\r\n").encode("ascii")
