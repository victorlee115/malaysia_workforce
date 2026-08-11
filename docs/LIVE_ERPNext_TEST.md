# Live ERPNext test procedure and current result

## Current result

The RC7 candidate passed a real isolated Frappe/ERPNext/HRMS bench on MariaDB 11.4.12. Clean installation, two consecutive migrations, asset build, eight live app tests and Chrome role acceptance completed successfully on the exact versions in `compatibility-lock.json`.

This is strong staging evidence, not business or regulatory production acceptance. See `ISOLATED_E2E_TEST_REPORT.md` and `RELEASE_VALIDATION.md`.

## Repeatable Bench test command

On a disposable Frappe 16 / ERPNext 16 / Frappe HR 16 bench with Python 3.14, Node 24, MariaDB 11.4 and Redis available:

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

The script verifies runtimes, installs the standard apps and Malaysia Workforce, migrates twice, builds assets, runs tests and diagnostics, and checks the live HTTP surface. Retain its logs as deployment evidence.

## Still required after the script passes

The automated harness does not replace business UAT. Complete the parallel payroll, bank/authority acceptance, physical kiosk, concurrency, recovery, security and specialist sign-off gates in `VALIDATION.md` before production activation.
