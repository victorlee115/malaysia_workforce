import csv
import hashlib
import json
from pathlib import Path

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


def test_all_doctype_json_is_parseable():
	root = Path(__file__).resolve().parents[1]
	for path in root.rglob("*.json"):
		json.loads(path.read_text())
