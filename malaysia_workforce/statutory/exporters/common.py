from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any


def ascii_text(value: Any) -> str:
	text = "" if value is None else str(value)
	return text.encode("ascii", errors="ignore").decode("ascii")


def fixed_text(value: Any, length: int, *, align: str = "left", fill: str = " ", uppercase: bool = False) -> str:
	text = ascii_text(value)
	if uppercase:
		text = text.upper()
	if len(text) > length:
		text = text[:length]
	return text.rjust(length, fill) if align == "right" else text.ljust(length, fill)


def digits(value: Any) -> str:
	return re.sub(r"\D", "", "" if value is None else str(value))


def cents(value: Any, length: int) -> str:
	try:
		amount = Decimal(str(value or 0))
	except (InvalidOperation, TypeError, ValueError) as exc:
		raise ValueError(f"Amount {value!r} is not numeric") from exc
	if not amount.is_finite():
		raise ValueError("Amount must be finite")
	if amount < 0:
		raise ValueError("Amount cannot be negative")
	amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
	integer = str(int(amount * 100))
	if len(integer) > length:
		raise ValueError(f"Amount {amount} exceeds {length}-digit fixed-width field")
	return integer.zfill(length)


def assert_length(record: str, expected: int, label: str) -> str:
	if len(record) != expected:
		raise ValueError(f"{label} must be exactly {expected} characters; generated {len(record)}")
	return record
