# Release validation report

**Release:** 1.0.0-rc.11

**Validation date:** 2026-08-13

**Pinned stack:** Frappe 16.31.0 / ERPNext 16.31.1 / HRMS 16.16.0 / Python 3.14 / Node 24 / MariaDB 11.4

## Decision

RC11 is a lean, existing-site MariaDB- and Chrome-tested staging/UAT candidate. Employee TP1/TP3 self-service and payslip PDF download now pass, but the release is **not production ready** while clean upstream site bootstrap, external authority acceptance, parallel payroll, recovery/security drills and specialist sign-off remain open.

## Architecture verified

Standard Frappe HR remains authoritative for Employee, Contract, Salary Structure, Additional Salary, Overtime Slip, Payroll Entry and Salary Slip. The app adds Malaysian fields, calculations, tax inputs and filing preparation to those workflows.

The former availability, staffing, roster, employee-profile, work-agreement, shift-work-record, kiosk, bank and parallel payroll-run features have been removed. Migration patches retire their DocTypes, fields, workspace and roles.

## Completed checks

- Pure calculator, data-integrity, wage and template tests.
- Python compilation and JavaScript syntax validation. The app ships no standalone frontend bundle; its Desk JavaScript is loaded through standard DocType hooks.
- Two consecutive migrations on the isolated MariaDB existing site.
- Standard Payroll Entry → Salary Slip live scenario with submit-time readiness validation.
- Unsupported/incomplete setup rejection and statutory-filing source-tamper detection.
- Cross-company report permission isolation and identity-sensitive filing fingerprints.
- LINDUNG release-window, multiple-employer, HRD headcount, TP3 evidence and CP38 remaining-balance guardrails.
- Calendar-month overtime aggregation across non-overlapping pending/submitted slips.
- Employee TP1/TP3 Web Form save → native `Send for Review` Workflow handoff, including retry safety, HR approval and two distinct previous employers.
- Monthly/full-time and hourly/part-time overtime integration through standard Overtime Slip and Additional Salary.
- EPF, PERKESO, LHDN and HRD Corp preparation/reconciliation state machines.
- Company/Employee permissions and read-only Auditor behaviour.
- Chrome desktop/mobile role-screen acceptance, including TP1 and TP3 submission at 390 × 844 with no horizontal overflow and native HR Workflow actions; see [the isolated test report](ISOLATED_E2E_TEST_REPORT.md).
- Source-table checksum, working-tree verification and exact working-tree Git-archive verification. A clean signed tag remains a release gate.

## Statutory calculation checks

Bundled LHDN PCB examples cover ordinary cumulative remuneration, TP1 relief and additional remuneration. The suite also covers effective-dated EPF, SOCSO/LINDUNG, EIS, HRD levy, minimum wage, monthly incomplete-month pay, hourly/daily wages, overtime, rest-day and public-holiday calculations, controlled TP1/TP3 relief codes, CP38, zakat rebate, invalid numeric data and unsupported scope rejection. LINDUNG 24 Jam coverage includes the opt-out default, the 1 June 2026 start, existing/new-employee release windows and unsupported multiple-employer rejection.

These tests validate deterministic software behaviour against the bundled reviewed rule pack. They are not statutory certification.

## Known blocker

Pinned Frappe 16.31.0 currently fails a brand-new MariaDB site bootstrap before this app is installed because the framework inserts the DocType field `protect_attached_files` before its bootstrap table contains that column. Existing-site migration succeeds. No local core patch is included; retest and update the compatibility lock when an official Frappe release resolves the mismatch.

## External gates

- Clean installation on an official compatible pinned stack.
- Official portal/validator UAT for EPF i-Akaun, PERKESO/ASSIST, LHDN and HRD Corp artifacts.
- Two parallel payroll periods and one off-cycle or year-boundary case with zero unexplained employee or authority differences.
- Backup restoration, concurrency, security, permission and failure-recovery drills.
- Written Malaysian payroll specialist and employer acceptance.

Live deployment must remain blocked until every gate in [VALIDATION.md](VALIDATION.md) is evidenced.
