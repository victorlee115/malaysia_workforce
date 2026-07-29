# Live ERPNext test procedure and current result

## Current execution result

A genuine ERPNext runtime could **not** be started in the build sandbox used for RC3. The sandbox had adequate CPU, memory and disk, but did not contain Frappe, ERPNext, Frappe HR, Bench, MariaDB or Redis. Docker/Podman were unavailable, and the configured internal APT repository returned HTTP 404 for Debian Release metadata. External source/package downloads were blocked by the sandbox network policy.

This is an infrastructure limitation, not a passing live test. RC3 therefore remains a staging candidate and is not production-certified.

## Checks completed in the sandbox

- Pure calculation and exporter tests
- Python compilation
- JavaScript syntax validation
- JSON duplicate-key and DocType contract checks
- Jinja print-format parsing
- Hook/API target resolution
- Statutory table checksum verification
- Archive and release-manifest verification
- Security-oriented source contracts

## Real Bench test command

On a disposable Frappe 16 / ERPNext 16 / Frappe HR 16 bench with Python 3.14, Node 24, MariaDB 11.8 and Redis available:

```bash
cd /path/to/frappe-bench

BENCH_DIR="$PWD" \
SITE="mw-live-test.localhost" \
APP_SOURCE="/path/to/malaysia_workforce" \
DB_ROOT_PASSWORD="your-db-root-password" \
ADMIN_PASSWORD="temporary-admin-password" \
KEEP_SITE=1 \
/path/to/malaysia_workforce/scripts/run_live_bench_test.sh
```

The script:

1. Verifies Python, Node and source prerequisites.
2. Creates a disposable site when requested.
3. Installs ERPNext, Frappe HR and Malaysia Workforce.
4. Runs migration twice to test idempotency.
5. Builds assets.
6. Runs the pure/static suite with the Bench virtual-environment Python.
7. Runs the live Frappe database/schema integration module through `bench --site ... run-tests`.
8. Runs `bench doctor`.
9. Starts the development processes and validates `/api/method/ping` over HTTP.
10. Optionally validates a configured Malaysian company when `COMPANY` is supplied.
11. Retains logs under `frappe-bench/logs/malaysia-workforce-live-test`.

## Still required after the script passes

The automated script does not replace business UAT. Complete the roster, attendance, payroll, accounting, permission, scheduler, mobile/browser and authority-upload scenarios in `docs/VALIDATION.md`, including two parallel payroll periods and actual portal acceptance evidence.
