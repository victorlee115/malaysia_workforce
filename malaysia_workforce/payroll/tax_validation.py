from __future__ import annotations

import json
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

MAX_DECLARATION_ROWS = 100
TP1_RULE_PATH = Path(__file__).resolve().parents[1] / "statutory" / "data" / "tp1_reliefs_2026.json"
TP3_MONEY_FIELDS = (
	"gross_normal_remuneration",
	"gross_additional_remuneration",
	"epf_contribution",
	"mtd_paid",
	"zakat_paid",
	"optional_reliefs",
)


def load_tp1_relief_rules(tax_year: int) -> dict[str, dict[str, Any]]:
	data = json.loads(TP1_RULE_PATH.read_text(encoding="utf-8"))
	if int(data.get("effective_year") or 0) != int(tax_year):
		raise ValueError(f"No reviewed TP1 relief catalogue is installed for tax year {tax_year}.")
	return data["reliefs"]


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
	if not amount.is_finite() or amount < 0:
		raise ValueError(f"{label} must be a non-negative finite amount.")
	return amount


def validate_tp1_rows(rows: list[dict], *, tax_year: int) -> list[dict]:
	if len(rows) > MAX_DECLARATION_ROWS:
		raise ValueError(f"No more than {MAX_DECLARATION_ROWS} relief claims may be submitted at once.")
	rules = load_tp1_relief_rules(tax_year)
	totals: dict[str, Decimal] = {}
	seen: set[tuple[str, str]] = set()
	cleaned = []
	for index, row in enumerate(rows, 1):
		code = str(row.get("relief_code") or "").strip().upper()
		if code not in rules:
			raise ValueError(f"Row {index}: {code or 'blank'} is not a valid TP1 code for {tax_year}.")
		amount = nonnegative_decimal(row.get("amount"), f"Row {index} amount")
		if amount == 0:
			raise ValueError(f"Row {index}: Amount must be greater than zero.")
		month = int(row.get("claim_month") or 0)
		if not 1 <= month <= 12:
			raise ValueError(f"Row {index}: Claim Month must be between 1 and 12.")
		evidence = str(row.get("evidence_reference") or "").strip()
		if rules[code].get("evidence_required") and not evidence:
			raise ValueError(f"Row {index}: Evidence Reference is required for {code}.")
		key = (code, evidence.casefold())
		if evidence and key in seen:
			raise ValueError(f"Row {index}: duplicate evidence reference for {code}.")
		seen.add(key)
		totals[code] = totals.get(code, Decimal("0")) + amount
		limit = Decimal(str(rules[code]["annual_limit"]))
		if totals[code] > limit:
			raise ValueError(f"Relief {code} exceeds its RM {limit:.2f} annual limit for {tax_year}.")
		cleaned.append({
			"relief_code": code,
			"description": rules[code]["label"],
			"amount": amount,
			"claim_month": month,
			"evidence_reference": evidence,
			"notes": str(row.get("notes") or "").strip()[:2000],
		})
	return cleaned


def manual_review_codes(rows: list[dict], *, tax_year: int) -> list[str]:
	rules = load_tp1_relief_rules(tax_year)
	return sorted(
		{
			str(row.get("relief_code") or "")
			for row in rows
			if row.get("relief_code") in rules
			and any(
				str(key).startswith("requires_manual_") and value
				for key, value in rules[row["relief_code"]].items()
			)
		}
	)


def submitted_relief_rows(
	doctype: str,
	*,
	employee: str,
	company: str,
	tax_year: int,
	exclude: str | None = None,
) -> list[dict]:
	"""Load every approved declaration row that shares the employee's annual cap."""
	import frappe

	filters: dict[str, Any] = {
		"employee": employee,
		"company": company,
		"tax_year": tax_year,
		"docstatus": 1,
	}
	if exclude:
		filters["name"] = ["!=", exclude]
	parents = frappe.get_all(doctype, filters=filters, pluck="name")
	if not parents:
		return []
	return [
		dict(row)
		for row in frappe.get_all(
			"Malaysia Tax Relief Claim",
			filters={"parent": ["in", parents], "parenttype": doctype},
			fields=["relief_code", "amount", "claim_month", "evidence_reference", "notes"],
		)
	]


def date_overlaps_tax_year(start: date | None, end: date | None, tax_year: int) -> bool:
	period_start, period_end = date(tax_year, 1, 1), date(tax_year, 12, 31)
	return (start or period_start) <= period_end and (end or period_end) >= period_start
