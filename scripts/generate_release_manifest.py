#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "RELEASE_MANIFEST.json"
IGNORED_NAMES = {".DS_Store", "RELEASE_MANIFEST.json"}
IGNORED_PARTS = {".git", ".pytest_cache", "__pycache__", "node_modules"}


def repository_paths() -> list[Path]:
	"""Return only files represented by the Git release index."""
	result = subprocess.run(
		["git", "ls-files", "--cached", "-z"],
		cwd=ROOT,
		check=True,
		capture_output=True,
	)
	paths = []
	for raw in result.stdout.split(b"\0"):
		if not raw:
			continue
		relative = Path(raw.decode("utf-8"))
		if relative.name in IGNORED_NAMES or any(part in IGNORED_PARTS for part in relative.parts):
			continue
		path = ROOT / relative
		if path.is_file():
			paths.append(path)
	return sorted(paths, key=lambda path: path.relative_to(ROOT).as_posix())


def build_manifest(release_date: str) -> dict:
	package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
	rows = []
	for path in repository_paths():
		content = path.read_bytes()
		rows.append(
			{
				"path": path.relative_to(ROOT).as_posix(),
				"size": len(content),
				"sha256": hashlib.sha256(content).hexdigest(),
			}
		)
	return {
		"app": "malaysia_workforce",
		"version": package["version"],
		"generated_on": release_date,
		"file_count": len(rows),
		"files": rows,
	}


def main() -> int:
	parser = argparse.ArgumentParser(description="Generate a deterministic release file manifest")
	parser.add_argument("--date", required=True, help="Release date in YYYY-MM-DD form")
	args = parser.parse_args()
	MANIFEST.write_text(json.dumps(build_manifest(args.date), indent=2) + "\n", encoding="utf-8")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
