# Installation

## Supported versions

This release deliberately refuses installation outside Frappe major version 16. The certification candidate is pinned in `compatibility-lock.json`; do not call another patch set production-tested until the live matrix is repeated.

Recommended prerequisites:

- a current supported Frappe v16 deployment;
- MariaDB 11.4, Python 3.14 and Node 24 for the tested candidate, plus the Redis version supported by the pinned Frappe stack;
- HTTPS, background workers and scheduler enabled;
- a recent database and sites backup;
- a separate staging site with anonymised or controlled payroll test data.

## Install from a local directory or ZIP

```bash
cd /path/to/frappe-bench
unzip malaysia_workforce-1.0.0-rc.7.zip -d /tmp
mv /tmp/malaysia_workforce apps/malaysia_workforce
./env/bin/pip install -e apps/malaysia_workforce
bench --site staging.example.com install-app malaysia_workforce
bench --site staging.example.com migrate
bench build --app malaysia_workforce
bench restart
```

Verify:

```bash
bench --site staging.example.com list-apps
bench --site staging.example.com execute malaysia_workforce.diagnostics.run
bench doctor
```

## Install from Git

```bash
bench get-app --branch release/1.0 https://your-git-host/malaysia_workforce.git
bench --site staging.example.com install-app malaysia_workforce
bench --site staging.example.com migrate
bench build --app malaysia_workforce
bench restart
```

## What installation creates

Installation and migration are idempotent. They create or update:

- Malaysia Workforce DocTypes and Workspace;
- custom fields on Employee, Company, Salary Component, Shift Assignment, Shift Type, Employee Checkin, Additional Salary, Salary Slip, Payroll Entry and Journal Entry;
- seven application roles, including a desk-disabled kiosk role;
- casual/part-time Employment Types;
- Malaysian payroll Salary Components;
- preparation Print Formats.

The installer does not create company-specific accounts, statutory numbers, employees, Salary Structures, Holiday Lists or portal credentials.

## Scheduler and workers

The app uses Frappe background workers and scheduler jobs for availability cutoffs, reminders, stale proposals, expired priorities, attendance reconciliation, compliance checks and accumulator rebuilds. Ensure scheduler and workers are healthy:

```bash
bench --site staging.example.com enable-scheduler
bench doctor
```

## Upgrade-safe deployment sequence

```bash
bench --site your-site backup --with-files
bench update --reset  # only according to your normal controlled Frappe process
bench --site your-site migrate
bench build --app malaysia_workforce
bench restart
bench --site your-site execute malaysia_workforce.diagnostics.run
```

Never edit files inside `erpnext` or `hrms` for this localisation.

## Uninstallation

Export all payroll, statutory submissions, generated files, acknowledgements and audit history first. Then:

```bash
bench --site your-site uninstall-app malaysia_workforce
```

Custom fields are intentionally retained by the uninstall hook to avoid destructive payroll data loss. Remove them only after a verified archive and legal-retention review.

## Disposable live-test harness

After preparing a supported v16 Bench, run `scripts/run_live_bench_test.sh`. The script installs the app, migrates twice, builds assets, runs tests and diagnostics, starts the development processes and verifies the ERPNext HTTP ping endpoint. See `docs/LIVE_ERPNext_TEST.md`.
