from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

RULE_PACK = "MY-2026.2"
DATA_DIR = Path(__file__).resolve().parent / "data"
RULE_FILES = (
	"epf_part_a_2025.csv",
	"epf_part_c_2025.csv",
	"epf_part_e_2025.csv",
	"socso_skbbk_2026.csv",
	"eis_2024.csv",
	"minimum_wage_2025.json",
	"pay_rules_2026.json",
	"tp1_reliefs_2026.json",
	"source_manifest.json",
)


def rule_pack_hash() -> str:
	digest = hashlib.sha256()
	for name in RULE_FILES:
		digest.update(name.encode())
		digest.update(b"\0")
		digest.update((DATA_DIR / name).read_bytes())
		digest.update(b"\0")
	return digest.hexdigest()


def reviewed_through() -> date:
	value = json.loads((DATA_DIR / "source_manifest.json").read_text())["reviewed_through"]
	return date.fromisoformat(value)
