from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any
import json
from pathlib import Path

MAX_DECLARATION_ROWS = 100
MAX_DATA_LENGTH = 140
MAX_NOTES_LENGTH = 2000
TP1_RULE_PATH = Path(__file__).resolve().parents[1] / "statutory" / "data" / "tp1_reliefs_2026.json"


def load_tp1_relief_rules(tax_year: int = 2026) -> dict[str, dict[str, Any]]:
	data = json.loads(TP1_RULE_PATH.read_text(encoding="utf-8"))
	if int(data.get("effective_year") or 0) != int(tax_year):
		raise ValueError(f"No reviewed TP1 relief catalogue is installed for tax year {tax_year}.")
	return data["reliefs"]

TP3_MONEY_FIELDS = (
	"gross_normal_remuneration",
	"gross_additional_remuneration",
	"epf_contribution",
	"mtd_paid",
	"zakat_paid",
	"optional_reliefs",
)


def validate_tax_year(value: Any, current_year: int) -> int:
	try:
		year = int(value)
	except (TypeError, ValueError) as exc:
		raise ValueError("Tax Year must be a whole number.") from exc
	if year < 2000 or year > current_year + 1:
		raise ValueError(f"Tax Year must be between 2000 and {current_year + 1}.")
	return year


def nonnegative_decimal(value: Any, label: str) -> Decimal:
	try:
		amount = Decimal(str(value or 0))
	except (InvalidOperation, TypeError, ValueError) as exc:
		raise ValueError(f"{label} must be a valid amount.") from exc
	if not amount.is_finite():
		raise ValueError(f"{label} must be a finite amount.")
	if amount < 0:
		raise ValueError(f"{label} cannot be negative.")
	return amount


def bounded_text(value: Any, label: str, maximum: int = MAX_DATA_LENGTH, *, required: bool = False) -> str:
	text = str(value or "").strip()
	if required and not text:
		raise ValueError(f"{label} is required.")
	if len(text) > maximum:
		raise ValueError(f"{label} cannot exceed {maximum} characters.")
	return text


def validate_tp1_rows(rows: Any, *, tax_year: int = 2026) -> list[dict[str, Any]]:
	if not isinstance(rows, list):
		raise ValueError("Relief Claims must be a list.")
	if len(rows) > MAX_DECLARATION_ROWS:
		raise ValueError(f"No more than {MAX_DECLARATION_ROWS} relief claims may be submitted at once.")
	cleaned: list[dict[str, Any]] = []
	rules = load_tp1_relief_rules(tax_year)
	totals: dict[str, Decimal] = {}
	seen_evidence: set[tuple[str, str]] = set()
	for index, row in enumerate(rows, start=1):
		if not isinstance(row, dict):
			raise ValueError(f"Relief claim row {index} must be an object.")
		month_value = row.get("claim_month")
		if month_value in (None, ""):
			month = None
		else:
			try:
				month = int(month_value)
			except (TypeError, ValueError) as exc:
				raise ValueError(f"Relief claim row {index}: Claim Month must be a whole number.") from exc
			if not 1 <= month <= 12:
				raise ValueError(f"Relief claim row {index}: Claim Month must be between 1 and 12.")
		code = bounded_text(
			row.get("relief_code"),
			f"Relief claim row {index}: Relief Code",
			required=True,
		).upper()
		if code not in rules:
			raise ValueError(f"Relief claim row {index}: {code} is not a valid TP1 code for {tax_year}.")
		amount = nonnegative_decimal(row.get("amount"), f"Relief claim row {index}: Amount")
		if amount <= 0:
			raise ValueError(f"Relief claim row {index}: Amount must be greater than zero.")
		evidence = bounded_text(
			row.get("evidence_reference") or row.get("receipt_reference"),
			f"Relief claim row {index}: Evidence Reference",
			required=bool(rules[code].get("evidence_required")),
		)
		evidence_key = (code, evidence.casefold())
		if evidence_key in seen_evidence:
			raise ValueError(f"Relief claim row {index}: duplicate evidence reference for {code}.")
		seen_evidence.add(evidence_key)
		totals[code] = totals.get(code, Decimal("0")) + amount
		limit = Decimal(str(rules[code]["annual_limit"]))
		if totals[code] > limit:
			raise ValueError(f"Relief {code} exceeds its RM {limit:.2f} annual limit for {tax_year}.")
		cleaned.append(
			{
				"relief_code": code,
				"description": rules[code]["label"],
				"amount": amount,
				"claim_month": month,
				"evidence_reference": evidence,
				"notes": bounded_text(
					row.get("notes"),
					f"Relief claim row {index}: Notes",
					MAX_NOTES_LENGTH,
				),
			}
		)
	return cleaned


def validate_tp3_values(values: dict[str, Any], current_year: int) -> dict[str, Any]:
	cleaned: dict[str, Any] = {
		"tax_year": validate_tax_year(values.get("tax_year"), current_year),
		"previous_employer_name": bounded_text(
			values.get("previous_employer_name"),
			"Previous Employer Name",
			required=True,
		),
		"previous_employer_number": bounded_text(
			values.get("previous_employer_number"),
			"Previous Employer Number",
		),
		"employment_start": values.get("employment_start") or None,
		"employment_end": values.get("employment_end") or None,
	}
	for fieldname in TP3_MONEY_FIELDS:
		cleaned[fieldname] = nonnegative_decimal(values.get(fieldname), fieldname.replace("_", " ").title())
	declaration = values.get("employee_declaration")
	if declaration not in (1, "1", True, "true", "True"):
		raise ValueError("The employee declaration must be accepted before submission.")
	cleaned["employee_declaration"] = 1
	return cleaned


def date_overlaps_tax_year(start: date | None, end: date | None, tax_year: int) -> bool:
	if not start and not end:
		return True
	period_start = date(tax_year, 1, 1)
	period_end = date(tax_year, 12, 31)
	actual_start = start or period_start
	actual_end = end or period_end
	return actual_start <= period_end and actual_end >= period_start
