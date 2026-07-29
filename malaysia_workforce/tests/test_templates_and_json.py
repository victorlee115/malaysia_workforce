import json
from pathlib import Path

from jinja2 import Environment

from malaysia_workforce.setup.print_formats import PRINT_FORMATS

ROOT = Path(__file__).resolve().parents[2]


def _reject_duplicate_keys(pairs):
	result = {}
	for key, value in pairs:
		if key in result:
			raise ValueError(f"duplicate JSON key: {key}")
		result[key] = value
	return result


def test_all_json_files_reject_duplicate_keys():
	for path in ROOT.rglob("*.json"):
		if any(part in {".pytest_cache", "__pycache__", "node_modules", ".git"} for part in path.parts):
			continue
		json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)


def test_all_print_formats_parse_as_jinja():
	environment = Environment()
	for definition in PRINT_FORMATS.values():
		environment.parse(definition["html"])
