#!/usr/bin/env python3
from __future__ import annotations

import ast
import argparse
import hashlib
import json
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "malaysia_workforce"
ERRORS: list[str] = []
SKIP_PARTS = {".pytest_cache", "__pycache__", "node_modules", ".git"}
SKIP_NAMES = {".DS_Store", "RELEASE_MANIFEST.json"}


def fail(message: str) -> None:
	ERRORS.append(message)


def reject_duplicate_json_keys(pairs):
	result = {}
	for key, value in pairs:
		if key in result:
			raise ValueError(f"duplicate JSON key: {key}")
		result[key] = value
	return result


def read_version() -> str:
	text = (PKG / "__init__.py").read_text(encoding="utf-8")
	match = re.search(r'__version__\s*=\s*"([^"]+)"', text)
	if not match:
		fail("Python package version is missing")
		return ""
	return match.group(1)


def package_version() -> str:
	return json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["version"]


def check_versions_and_runtime() -> None:
	python_version = read_version()
	js_version = package_version()
	if python_version != js_version.replace("-rc.", "rc"):
		fail(f"Version mismatch: Python={python_version}, package.json={js_version}")
	pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
	package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
	for expected in (
		'requires-python = ">=3.14,<3.15"',
		'frappe = "==16.31.0"',
		'erpnext = "==16.31.1"',
		'hrms = "==16.16.0"',
	):
		if expected not in pyproject:
			fail(f"Missing runtime/dependency pin: {expected}")
	if package.get("engines", {}).get("node") != ">=24":
		fail("package.json must require Node >=24 for Frappe v16")
	lock = json.loads((ROOT / "compatibility-lock.json").read_text(encoding="utf-8"))
	for app, expected in (("frappe", "16.31.0"), ("erpnext", "16.31.1"), ("hrms", "16.16.0")):
		if lock.get("apps", {}).get(app, {}).get("version") != expected:
			fail(f"compatibility-lock.json does not pin {app} {expected}")
	if lock.get("runtime", {}).get("database") != "MariaDB 11.4":
		fail("compatibility-lock.json must pin the tested MariaDB 11.4 series")
	if "image: mariadb:11.4" not in (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"):
		fail("CI must exercise the tested MariaDB 11.4 series")


def check_required_files() -> None:
	for relative in (
		"README.md",
		"CHANGELOG.md",
		"license.txt",
		"pyproject.toml",
		"docs/INSTALLATION.md",
		"docs/CONFIGURATION.md",
		"docs/OPERATIONS.md",
		"docs/USER_GUIDE.md",
		"docs/VALIDATION.md",
		"docs/RELEASE_VALIDATION.md",
		"scripts/run_live_bench_test.sh",
		"scripts/generate_release_manifest.py",
		"compatibility-lock.json",
		"malaysia_workforce/live_tests/scenarios.py",
	):
		path = ROOT / relative
		if not path.exists() or path.stat().st_size == 0:
			fail(f"Required release file is missing or empty: {relative}")


def check_no_stale_release_markers() -> None:
	for relative in (
		"README.md",
		"docs/INSTALLATION.md",
		"docs/VALIDATION.md",
		"docs/RELEASE_VALIDATION.md",
		"malaysia_workforce/install.py",
	):
		text = (ROOT / relative).read_text(encoding="utf-8")
		for marker in ("1.0.0-rc.9", "1.0.0rc9"):
			if marker in text:
				fail(f"Stale release marker {marker} in {relative}")


def check_json_and_doctypes() -> None:
	custom_names = set()
	doctype_files = list((PKG / "malaysia_workforce" / "doctype").glob("*/*.json"))
	for path in doctype_files:
		try:
			custom_names.add(json.loads(path.read_text(encoding="utf-8"))["name"])
		except Exception as exc:
			fail(f"Invalid DocType JSON {path.relative_to(ROOT)}: {exc}")
	for path in ROOT.rglob("*.json"):
		if any(part in SKIP_PARTS for part in path.parts):
			continue
		try:
			data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_json_keys)
		except Exception as exc:
			fail(f"Invalid JSON {path.relative_to(ROOT)}: {exc}")
			continue
		if path not in doctype_files:
			continue
		fields = data.get("fields", [])
		fieldnames = [row.get("fieldname") for row in fields]
		field_order = data.get("field_order", [])
		if len(fieldnames) != len(set(fieldnames)):
			fail(f"Duplicate DocType fieldname in {path.relative_to(ROOT)}")
		if set(fieldnames) != set(field_order) or len(field_order) != len(set(field_order)):
			fail(f"DocType field_order mismatch in {path.relative_to(ROOT)}")
		for row in fields:
			if row.get("fieldtype") == "Table" and row.get("options") not in custom_names:
				fail(f"Unknown child table {row.get('options')} in {path.relative_to(ROOT)}")


def check_python() -> None:
	for path in PKG.rglob("*.py"):
		try:
			compile(path.read_text(encoding="utf-8"), str(path), "exec")
		except Exception as exc:
			fail(f"Python compile failed {path.relative_to(ROOT)}: {exc}")


def module_file(module: str) -> Path | None:
	if not module.startswith("malaysia_workforce"):
		return None
	candidate = ROOT.joinpath(*module.split("."))
	if candidate.with_suffix(".py").exists():
		return candidate.with_suffix(".py")
	if (candidate / "__init__.py").exists():
		return candidate / "__init__.py"
	return None


def target_exists(dotted: str) -> bool:
	parts = dotted.split(".")
	for index in range(len(parts), 1, -1):
		path = module_file(".".join(parts[:index]))
		if not path:
			continue
		attrs = parts[index:]
		if not attrs:
			return True
		tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
		names = {
			node.name
			for node in tree.body
			if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
		}
		return attrs[0] in names
	return False


def check_internal_references() -> None:
	for path in PKG.rglob("*.py"):
		tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
		for node in ast.walk(tree):
			if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("malaysia_workforce"):
				if not module_file(node.module):
					fail(f"Missing internal module {node.module} imported by {path.relative_to(ROOT)}")
			elif isinstance(node, ast.Import):
				for alias in node.names:
					if alias.name.startswith("malaysia_workforce") and not module_file(alias.name):
						fail(f"Missing internal module {alias.name} imported by {path.relative_to(ROOT)}")

	hooks = (PKG / "hooks.py").read_text(encoding="utf-8")
	for dotted in sorted(set(re.findall(r'"(malaysia_workforce\.[A-Za-z0-9_.]+)"', hooks))):
		if dotted.endswith((".bundle.css", ".bundle.js")):
			basename = dotted.split(".")[0] + ".bundle." + dotted.rsplit(".", 1)[-1]
			if not any(path.name == basename for path in (PKG / "public").rglob("*")):
				fail(f"Missing bundle source for {dotted}")
		elif not target_exists(dotted):
			fail(f"Hook/scheduler target does not resolve: {dotted}")

	for line in (PKG / "patches.txt").read_text(encoding="utf-8").splitlines():
		line = line.strip()
		if not line or line.startswith("#") or (line.startswith("[") and line.endswith("]")):
			continue
		if not module_file(line):
			fail(f"Patch module does not resolve: {line}")

	for path in PKG.rglob("*.js"):
		text = path.read_text(encoding="utf-8")
		for dotted in sorted(set(re.findall(r'["\'](malaysia_workforce\.[A-Za-z0-9_.]+)["\']', text))):
			if dotted.endswith((".bundle.css", ".bundle.js")):
				continue
			if not target_exists(dotted):
				fail(f"JavaScript API target does not resolve: {dotted} in {path.relative_to(ROOT)}")


def check_rule_hashes() -> None:
	data = PKG / "statutory" / "data"
	manifest = json.loads((data / "source_manifest.json").read_text(encoding="utf-8"))
	for filename, expected in manifest["generated_tables"].items():
		path = data / filename
		if not path.exists():
			fail(f"Missing rule table: {filename}")
			continue
		actual = hashlib.sha256(path.read_bytes()).hexdigest()
		if actual != expected["sha256"]:
			fail(f"Rule table hash mismatch: {filename}")


def check_javascript() -> None:
	try:
		for path in PKG.rglob("*.js"):
			result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True)
			if result.returncode:
				fail(f"JavaScript syntax failed {path.relative_to(ROOT)}: {result.stderr.strip()}")
	except FileNotFoundError:
		print("warning: node is unavailable; JavaScript syntax check skipped", file=sys.stderr)


def release_files() -> list[Path]:
	try:
		result = subprocess.run(
			["git", "ls-files", "--cached", "-z"],
			cwd=ROOT,
			check=True,
			capture_output=True,
		)
		paths = [ROOT / Path(raw.decode("utf-8")) for raw in result.stdout.split(b"\0") if raw]
	except (FileNotFoundError, subprocess.CalledProcessError):
		paths = list(ROOT.rglob("*"))
	return sorted(
		path
		for path in paths
		if path.is_file()
		and path.name not in SKIP_NAMES
		and not any(part in SKIP_PARTS for part in path.relative_to(ROOT).parts)
		and path.suffix != ".pyc"
	)


def check_release_manifest() -> None:
	path = ROOT / "RELEASE_MANIFEST.json"
	try:
		manifest = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_json_keys)
	except Exception as exc:
		fail(f"Release manifest is missing or invalid: {exc}")
		return
	if manifest.get("version") != package_version():
		fail("Release manifest version does not match package.json")
	actual_files = release_files()
	actual_rel = {str(item.relative_to(ROOT)) for item in actual_files}
	manifest_rows = manifest.get("files", [])
	manifest_rel = {row.get("path") for row in manifest_rows}
	if actual_rel != manifest_rel:
		missing = sorted(actual_rel - manifest_rel)
		extra = sorted(manifest_rel - actual_rel)
		fail(f"Release manifest file set mismatch; missing={missing[:5]}, extra={extra[:5]}")
	rows = {row["path"]: row for row in manifest_rows if row.get("path")}
	for item in actual_files:
		rel = str(item.relative_to(ROOT))
		row = rows.get(rel)
		if not row:
			continue
		if row.get("size") != item.stat().st_size:
			fail(f"Release manifest size mismatch: {rel}")
		if row.get("sha256") != hashlib.sha256(item.read_bytes()).hexdigest():
			fail(f"Release manifest hash mismatch: {rel}")
	if manifest.get("file_count") != len(actual_files):
		fail("Release manifest file_count is incorrect")


def check_no_build_junk() -> None:
	for path in ROOT.rglob("*"):
		if path.is_file() and ("__pycache__" in path.parts or ".pytest_cache" in path.parts or path.suffix == ".pyc"):
			fail(f"Build/cache artifact present: {path.relative_to(ROOT)}")


def verify_git_archive() -> int:
	"""Run the same verifier inside the exact Git release-index archive."""
	with tempfile.TemporaryDirectory(prefix="mw-release-") as temporary:
		archive = Path(temporary) / "release.tar"
		extracted = Path(temporary) / "release"
		extracted.mkdir()
		tree = subprocess.run(
			["git", "write-tree"], cwd=ROOT, check=True, capture_output=True, text=True
		).stdout.strip()
		subprocess.run(["git", "archive", tree, "-o", str(archive)], cwd=ROOT, check=True)
		with tarfile.open(archive) as handle:
			handle.extractall(extracted, filter="data")
		return subprocess.run([sys.executable, str(extracted / "scripts" / "verify_release.py")]).returncode


def main() -> int:
	parser = argparse.ArgumentParser(description="Verify a Malaysia Workforce release")
	parser.add_argument("--git-archive", action="store_true", help="verify the exact committed Git archive")
	args = parser.parse_args()
	if args.git_archive:
		return verify_git_archive()
	check_versions_and_runtime()
	check_required_files()
	check_no_stale_release_markers()
	check_json_and_doctypes()
	check_python()
	check_internal_references()
	check_rule_hashes()
	check_javascript()
	check_release_manifest()
	check_no_build_junk()
	if ERRORS:
		print("Release verification FAILED:")
		for error in ERRORS:
			print(f"- {error}")
		return 1
	print("Release verification passed.")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
