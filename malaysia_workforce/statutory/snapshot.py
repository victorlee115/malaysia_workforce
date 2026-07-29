from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from typing import Any

REQUIRED_WAGE_BASES = {"gross", "epf", "socso", "eis", "pcb_regular", "pcb_additional"}
RESULT_AMOUNT_FIELDS = {"wage_base", "employee_amount", "employer_amount", "extra_employee_amount"}


def _finite_decimal(value: Any, label: str) -> Decimal:
	try:
		amount = Decimal(str(value or 0))
	except (InvalidOperation, TypeError, ValueError) as exc:
		raise ValueError(f"{label} must be a valid amount.") from exc
	if not amount.is_finite():
		raise ValueError(f"{label} must be a finite amount.")
	return amount


def parse_json_object(value: str | dict | None, label: str) -> dict[str, Any]:
	if isinstance(value, dict):
		parsed = value
	else:
		if value in (None, ""):
			raise ValueError(f"{label} is empty.")
		try:
			parsed = json.loads(value)
		except (TypeError, ValueError) as exc:
			raise ValueError(f"{label} is not valid JSON: {exc}") from exc
	if not isinstance(parsed, dict):
		raise ValueError(f"{label} must be a JSON object.")
	return parsed


def _validate_results(value: Any, label: str) -> list[dict[str, Any]]:
	if not isinstance(value, list):
		raise ValueError(f"{label} must be a list.")
	for index, result in enumerate(value, start=1):
		if not isinstance(result, dict):
			raise ValueError(f"{label} row {index} must be an object.")
		if not str(result.get("scheme") or "").strip():
			raise ValueError(f"{label} row {index} has no scheme.")
		for fieldname in RESULT_AMOUNT_FIELDS:
			_finite_decimal(result.get(fieldname), f"{label} row {index} {fieldname}")
	return value


def parse_statutory_snapshot(value: str | dict | None) -> dict[str, Any]:
	snapshot = parse_json_object(value, "Malaysia statutory snapshot")
	wage_bases = snapshot.get("current_wage_bases")
	if not isinstance(wage_bases, dict):
		raise ValueError("Malaysia statutory snapshot current_wage_bases must be an object.")
	missing = sorted(REQUIRED_WAGE_BASES - set(wage_bases))
	if missing:
		raise ValueError(
			"Malaysia statutory snapshot is missing wage bases: " + ", ".join(missing) + "."
		)
	for fieldname in REQUIRED_WAGE_BASES:
		_finite_decimal(wage_bases.get(fieldname), f"Malaysia statutory snapshot wage base {fieldname}")
	_validate_results(snapshot.get("current_results"), "Malaysia statutory snapshot current_results")
	if "month_total_results" in snapshot:
		_validate_results(snapshot.get("month_total_results"), "Malaysia statutory snapshot month_total_results")
	for fieldname in ("current_cp38", "current_zakat"):
		if fieldname in snapshot:
			_finite_decimal(snapshot.get(fieldname), f"Malaysia statutory snapshot {fieldname}")
	return snapshot
