import csv
import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pytest

from malaysia_workforce.statutory.common import DATA_DIR


def test_generated_statutory_tables_match_manifest():
	manifest = json.loads((DATA_DIR / "source_manifest.json").read_text())
	for filename, expected in manifest["generated_tables"].items():
		path = DATA_DIR / filename
		assert path.exists(), filename
		assert hashlib.sha256(path.read_bytes()).hexdigest() == expected["sha256"]
		with path.open(newline="", encoding="utf-8") as handle:
			rows = sum(1 for _ in csv.DictReader(handle))
		assert rows == expected["rows"]
	for filename, expected in manifest["rule_files"].items():
		path = DATA_DIR / filename
		assert hashlib.sha256(path.read_bytes()).hexdigest() == expected["sha256"]


def test_all_doctype_json_is_parseable():
	root = Path(__file__).resolve().parents[1]
	for path in root.rglob("*.json"):
		json.loads(path.read_text())


def _round_trips(value: Decimal) -> bool:
	"""Simulates the app's write path (`float(money(...))` into a Currency field) followed
	by its read path (`Decimal(str(value))`, used by every reader) for one amount."""
	return Decimal(str(float(value))) == value


def test_currency_float_round_trip_every_cent_up_to_one_thousand():
	"""Exhaustively prove no cent value in an ordinary payroll range loses precision."""
	value = Decimal("0.00")
	step = Decimal("0.01")
	limit = Decimal("1000.00")
	while value <= limit:
		assert _round_trips(value), value
		value += step


@pytest.mark.parametrize(
	"base",
	[
		Decimal("9999"),
		Decimal("99999"),
		Decimal("999999"),
		Decimal("1000000"),
		Decimal("9999999"),
		Decimal("50000000"),
	],
)
def test_currency_float_round_trip_near_large_magnitudes(base):
	"""Aggregate filing totals sum many employees' contributions into large amounts."""
	for offset in (Decimal("0.00"), Decimal("0.01"), Decimal("0.50"), Decimal("0.99")):
		value = base + offset
		assert _round_trips(value), value


@pytest.mark.parametrize(
	"value",
	[
		Decimal("0.10"), Decimal("0.20"), Decimal("0.29"), Decimal("0.33"), Decimal("0.67"),
		Decimal("33.33"), Decimal("66.67"), Decimal("100.10"), Decimal("123456.78"),
	],
)
def test_currency_float_round_trip_known_awkward_fractions(value):
	"""These specific values are classic examples of binary-float representation error."""
	assert _round_trips(value)
