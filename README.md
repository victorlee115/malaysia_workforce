# Malaysia Payroll for Frappe HR

**Version:** 1.0.0-rc.14

**Tested stack:** Frappe 16.31.0, ERPNext 16.31.1, HRMS 16.16.0, Python 3.14, Node 24, MariaDB 11.4
**Licence:** GPL-3.0-or-later

Malaysia Workforce is a lean Malaysian payroll localisation for Frappe HR. It keeps standard Frappe HR records and screens authoritative and adds the statutory behaviour that the Malaysia country context needs.

*Naming note: the Frappe Module is `Malaysia Workforce` (internal grouping used by every doctype's `module` key) and the app title is `Malaysia Payroll` (the product name shown in the app list). This split is intentional, not an oversight — renaming the Module is a breaking, migration-relevant change out of scope for a cosmetic fix.*

It adds:

- effective-dated EPF, SOCSO, LINDUNG 24 Jam, EIS, PCB, HRD Corp and minimum-wage rules;
- statutory fields on standard `Company`, `Employee`, `Contract`, `Salary Component`, `Salary Slip` and `Overtime Type`;
- TP1 relief declarations, TP3 previous-employment amounts and CP38 directives;
- native overtime, rest-day and public-holiday calculations through HRMS `Overtime Slip`;
- deterministic statutory results on `Salary Slip`;
- a read-only readiness check on the standard `Payroll Entry` form;
- EPF, PERKESO, LHDN and HRD Corp preparation records with control totals and submission evidence;
- payroll-readiness and annual-remuneration reports.

It does **not** add employee profiles, employment agreements, recruitment, leave, attendance, rosters, bank payments, a custom employee portal, or a parallel payroll run. Use standard Frappe HR for those.

## Authoritative flow

```text
Company + Employee + Contract + Salary Components
    → Salary Structure Assignment / Additional Salary / Overtime Slip
    → standard Payroll Entry
    → standard Salary Slip with statutory deductions and calculation details
    → normal Frappe HR payroll submission and accounting
    → authority preparation records with human submission evidence
```

## Phase 1 scope

Phase 1 deliberately supports Peninsular Malaysia and Malaysian citizens or permanent residents under ordinary resident PCB treatment. Unsupported jurisdictions, foreign workers, incomplete statutory identities, missing contracts and dates beyond the reviewed rule pack fail closed.

The generated authority files are preparation artifacts. They never claim an authority accepted a submission unless a user records the evidence.

## Install and validate

Use the exact versions in [`compatibility-lock.json`](compatibility-lock.json). Install ERPNext and HRMS first, then this app:

```bash
bench get-app /path/to/malaysia_workforce
bench --site staging.example.com install-app malaysia_workforce
bench --site staging.example.com migrate
bench --site staging.example.com migrate
bench build --app malaysia_workforce
```

Run the local checks:

```bash
pytest -q
npm run check:js
python scripts/verify_release.py
```

The currently pinned upstream Frappe 16.31.0 release has a clean-site bootstrap defect described in [Release validation](docs/RELEASE_VALIDATION.md). Existing-site migration and the live Malaysia payroll scenario pass, but this release must not be promoted until a clean official stack installation, external authority acceptance, parallel payroll, recovery testing, and specialist review all pass.

## Documentation

- [Installation](docs/INSTALLATION.md)
- [Configuration](docs/CONFIGURATION.md)
- [User guide for every role](docs/USER_GUIDE.md)
- [Frappe HR ownership](docs/FRAPPE_HR_CONFIGURATION.md)
- [Payroll operations](docs/OPERATIONS.md)
- [Statutory scope](docs/LEGAL_AND_STATUTORY.md)
- [Security](docs/SECURITY.md)
- [Validation and go-live](docs/VALIDATION.md)
- [Release evidence](docs/RELEASE_VALIDATION.md)
- [Upgrade](docs/UPGRADE.md)
- [Public methods](docs/API.md)

The app can remove repetitive payroll administration. The employer still retains legal accountability and should obtain periodic Malaysian payroll and employment-law review.
