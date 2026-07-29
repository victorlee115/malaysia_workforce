# Malaysia Workforce for ERPNext/Frappe HR

**Version:** 1.0.0-rc.4  
**Supported stack:** Frappe 16, ERPNext 16 and Frappe HR 16  
**Licence:** GPL-3.0-or-later

Malaysia Workforce is an upgrade-safe Frappe app for Malaysian employee administration, casual open rosters, exact-hour applications, attendance, hourly payroll, employee-specific statutory treatment, statutory calculations, authority files and reconciliation.

This release is an installable **production-oriented release candidate**. It is not a substitute for employer legal responsibility, LHDN payroll-software verification, agency credentials, company-specific accounting configuration, parallel payroll or user acceptance testing.

## What is included

### Employee and casual-work experience

- Mobile-first portal at `/workforce`.
- Open rosters where eligible casual employees submit one or more exact availability windows.
- Employees may authorise the manager to choose any hours inside their windows, or require a final exact-hours confirmation.
- Split shifts use Frappe HR's standard **Allow Multiple Shift Assignments for Same Date** setting and are disabled unless it is enabled.
- Manager retains final control over employee selection and the exact assigned hours.
- Open work, pending offers, applications, confirmed shifts and mobile check-in/check-out.
- Employee time corrections with a manager review path.
- Own-record permissions for applications, selections, work records, TP1, TP3 and annual statements.

### Manager and HR experience

- Visual roster planner at `/desk/casual-roster-planner`.
- Coverage by date, role and time interval, with gap detection and explainable recommendations.
- Shift Assignment creation only after the worker is selected and, where required, accepts the exact hours.
- Attendance exception handling and approved `Shift Work Record` as the payable source of truth.
- Effective-dated work agreements and Malaysian employee profiles.
- Immediate per-employee statutory settings with warnings and immutable history; no approval workflow is imposed.

### Payroll

- Ordinary, part-time additional, overtime, rest-day and public-holiday pay bands.
- Minimum-hourly-rate checks and effective-dated work agreements.
- Idempotent conversion of approved work records to standard Frappe HR `Additional Salary` records.
- Standard Frappe HR `Payroll Entry` and `Salary Slip` integration.
- Month-to-date statutory accumulation across weekly, fortnightly, bimonthly, daily or monthly pay runs.
- Source hashes and frozen work-record ownership to prevent duplicate pay.
- Employer EPF, SOCSO and EIS Journal Entry generation when configured.

### Malaysian statutory calculations

- EPF/KWSP contribution schedules embedded as effective source tables.
- SOCSO, LINDUNG 24 Jam/SKBBK and EIS contribution schedules.
- LHDN computerised PCB calculation engine, including regular and additional remuneration, TP1, TP3, zakat and CP38 inputs.
- Scheme-specific wage classification on each Salary Component.
- `Automatic`, `Applicable`, `Not Applicable` and `Pending Review` treatment per employee and scheme.
- Submitted Salary Slip statutory snapshots are immutable.

### Forms and authority outputs

- Monthly LHDN PCB text file.
- Legacy EPF e-Caruman CSV serializer for isolated UAT only; disabled by default and never labelled portal-ready.
- PERKESO combined SOCSO/EIS/LINDUNG fixed-width file.
- TP1 and TP3 data-capture records and preparation printouts.
- CP21/CP22/CP22A/CP22B employee-notification preparation records.
- EA/EC annual remuneration preparation statements.
- CP8D and Form E preparation worksheets.
- Private generated files, SHA-256 checksums, schema version, portal link, submission reference, acknowledgement, receipt, payment and reconciliation.
- Revision workflow that preserves rejected and accepted evidence.

The TP1, TP3, notification, EA/EC, CP8D and Form E documents are explicitly labelled **preparation records**. Confirm current official layouts and portal fields before issue or filing. The LHDN and PERKESO monthly files are generated to their bundled schema versions and require authority acceptance testing. The bundled EPF CSV follows the retired e-Caruman guide, is disabled by default, and must not be used as current i-Akaun output.

## Architecture

The app does not modify ERPNext or Frappe HR core code. It extends standard records through custom fields and document hooks:

```text
Casual Roster
  -> Roster Application + exact availability windows
  -> Roster Selection
  -> standard Shift Assignment
  -> standard Employee Checkin
  -> Shift Work Record
  -> standard Additional Salary
  -> standard Payroll Entry and Salary Slip
  -> statutory snapshots and monthly submissions
```

Main standard records retained:

- Employee, Company, Branch, Shift Type, Shift Assignment and Employee Checkin.
- Salary Component, Salary Structure, Salary Structure Assignment, Additional Salary, Payroll Entry and Salary Slip.
- Journal Entry and File.

## Installation

Install on a staging site first:

```bash
cd /path/to/frappe-bench
bench get-app /path/to/malaysia_workforce
bench --site staging.example.com install-app malaysia_workforce
bench --site staging.example.com migrate
bench build --app malaysia_workforce
bench restart
```

For a ZIP distribution, extract the app into `frappe-bench/apps/malaysia_workforce`, then run:

```bash
./env/bin/pip install -e apps/malaysia_workforce
bench --site your-site install-app malaysia_workforce
bench --site your-site migrate
bench build --app malaysia_workforce
bench restart
```

Run the post-install diagnostic:

```bash
bench --site your-site execute malaysia_workforce.diagnostics.run
```

See [Installation](docs/INSTALLATION.md) and [Configuration](docs/CONFIGURATION.md).

## Minimum configuration before payroll

1. Set each Malaysian Company to country Malaysia, currency MYR and enable **Malaysia Payroll**.
2. Complete Company LHDN, EPF, SOCSO and SSM references.
3. Review `Malaysia Workforce Settings`, including rule-review date, minimum wage, portal URLs, payroll components and employer accounts.
4. Complete `Malaysia Employee Profile`, `Employee Work Agreement` and `Statutory Coverage Profile` for every employee.
5. Classify each earning Salary Component separately for EPF, SOCSO, EIS and PCB.
6. Configure a valid Salary Structure Assignment and Payroll Payable Account.
7. Run a minimum of two parallel payrolls and portal acceptance tests before production filing.

## Statutory overrides

There is intentionally no approval workflow for statutory treatment changes. Authorised HR/payroll users can save a scheme as `Not Applicable` immediately. The app still:

- warns where the employee is recorded under a contract of service;
- requires an effective period;
- records the old and new treatment, user, timestamp, reason and notes;
- marks open Salary Slips for recalculation;
- never rewrites submitted Salary Slips or submitted authority records.

## Government submission boundary

`submission_mode` supports `API`, `File Upload`, `Portal Only` and `Document Only`. The bundled adapters implement validated file generation and a portal-assistant workflow. They do not store government portal passwords, automate OTPs or claim a filing was submitted merely because a file was generated.

An API mode must only be enabled after the authority has issued an official interface specification, credentials, test environment and written permission for that employer/integrator. Implement that authority adapter without changing payroll or audit records.

### EPF file boundary

EPF discontinued the e-Caruman application on 31 October 2025 and moved contribution payment services to i-Akaun (Employer). RC3 therefore does not claim that the old six-column e-Caruman CSV is a current i-Akaun upload schema. The legacy serializer is disabled by default, labelled UAT-only, cannot become `Ready for Portal`, and cannot be marked as an official submission. A verified current EPF adapter is still required.

## Verification included in this release

The pure calculation suite contains 56 automated tests and includes:

- four published LHDN PCB worked examples, including the April bonus result of RM833.70;
- EPF, SOCSO/SKBBK and EIS contribution lookups;
- LHDN fixed-length output validation;
- PERKESO 278-character output validation;
- EPF legacy CSV field/header validation and fail-closed production controls;
- pay-band calculations and statutory source-table checksums;
- JSON and Python syntax checks.

Run:

```bash
cd apps/malaysia_workforce
pytest -q
python -m compileall -q malaysia_workforce
npm run check:js
python scripts/verify_release.py
```

Live Frappe integration, browser, database concurrency, payroll accounting and authority-portal tests must be run in your v16 staging environment. This build environment had no Frappe/ERPNext/HRMS source, Bench, database server or Redis server; the available browser could not substitute for the missing server runtime. See [Validation](docs/VALIDATION.md).

## Documentation

- [Installation](docs/INSTALLATION.md)
- [Configuration](docs/CONFIGURATION.md)
- [Operations](docs/OPERATIONS.md)
- [Statutory scope and limitations](docs/LEGAL_AND_STATUTORY.md)
- [Security](docs/SECURITY.md)
- [Validation and go-live](docs/VALIDATION.md)
- [Live ERPNext test procedure](docs/LIVE_ERPNext_TEST.md)
- [Build-environment limitation report](docs/BUILD_ENVIRONMENT_LIMITATION.md)
- [Release validation report](docs/RELEASE_VALIDATION.md)
- [Code audit and test report](docs/CODE_AUDIT_AND_TEST_REPORT.md)
- [API](docs/API.md)
- [Upgrade and rollback](docs/UPGRADE.md)

## Release-candidate boundaries

- Standby records, validation and expiry are included, but automated sequential standby-offer creation and cascade acceptance are not included in RC3.
- Annual and employee-notification documents are preparation worksheets, not a claim of official electronic filing.
- Direct government API submission remains an adapter boundary until an authority supplies an authorised interface and credentials.
- Production activation still requires live v16 staging, parallel payroll and authority-upload acceptance.

## Release status

This archive is suitable for staging installation and controlled production rollout after the validation gates in `docs/VALIDATION.md` are signed off. No software package can be safely “plug and play” for Malaysian payroll without employer master data, chart-of-accounts mapping, current authority acceptance and parallel payroll evidence.
