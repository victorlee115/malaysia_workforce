# Installation

## Supported stack

Install only on the exact versions in `compatibility-lock.json`: Frappe 16.31.0, ERPNext 16.31.1, HRMS 16.16.0, Python 3.14, Node 24 and MariaDB 11.4.

ERPNext and HRMS must already be installed:

```bash
cd /path/to/frappe-bench
bench get-app /path/to/malaysia_workforce
bench --site staging.example.com install-app malaysia_workforce
bench --site staging.example.com migrate
bench --site staging.example.com migrate
bench build --app malaysia_workforce
```

Do not use a production site for the first installation. The pinned Frappe release currently has an upstream clean-site bootstrap failure before this app can install; see `RELEASE_VALIDATION.md`. Use a clean official version only after that gate is resolved.

## What installation changes

The app creates only five Malaysian business records: TP1, TP3, CP38, Statutory Filing and their child tables. It adds Custom Fields to standard payroll records, creates reserved Malaysia Salary Components and Overtime Types, and installs a Malaysia Payroll Workspace and two reports.

It does not alter framework source files or create a custom Employee/Profile/Contract/Payroll Entry replacement.

## Initial verification

```bash
bench --site staging.example.com list-apps
bench --site staging.example.com execute malaysia_workforce.live_tests.scenarios.runtime_info
bench --site staging.example.com execute malaysia_workforce.diagnostics.get_diagnostics --kwargs '{"company":"Your Company"}'
```

Migration is intended to be idempotent. Run it twice in staging and inspect both outputs before go-live.
