# Code audit and test report

**Application:** Malaysia Workforce  
**Audited release:** 1.0.0-rc.3  
**Date:** 2026-07-29

## Audit method

The review covered all Python, JavaScript, JSON, CSV rule tables, hooks, patches, permissions, payroll lifecycle code, authority exporters and release metadata. Checks included source tracing against Frappe HR v16, targeted code review, pure unit tests, static contract tests, Python compilation, JavaScript syntax checks, JSON/DocType consistency, internal dotted-target resolution, checksum verification and release-manifest verification.

A live Frappe bench was unavailable, so this report distinguishes completed source-level verification from mandatory live integration testing.

## Material findings and corrections

### Critical/high

1. **Roster data isolation:** employee reads could expose open rosters from another company, while Roster Manager access was not restricted to the roster's assigned manager. Query conditions and document permission checks now enforce company and manager scope.
2. **Duplicate payroll risk:** two payroll runs could select the same approved Shift Work Record. RC2 locks and reserves payable rows with `SELECT ... FOR UPDATE`, records ownership and uses frozen source hashes.
3. **Incorrect payroll lifecycle:** Frappe HR submits Payroll Entry before its generated Salary Slips. Statutory files and employer journals were therefore being triggered too early. RC2 finalises only after every expected linked Salary Slip is submitted, under a run lock and idempotency checks.
4. **Unapproved time could be paid:** early arrival and late departure could enlarge automatically verified pay. The default policy now caps payable time to the confirmed assignment while still reducing pay for lateness or early departure.
5. **Malformed statutory history:** invalid submitted Salary Slip snapshots could be treated as absent/zero. Snapshot parsing now fails closed with an actionable error.
6. **Authority export corruption:** non-finite numbers, control characters and non-ASCII text could be accepted or silently altered. Exporters now validate numeric ranges and reject unsupported characters instead of dropping them.

### Medium

7. Standard Frappe HR Shift Assignments are included in overlap detection, including overnight shifts.
8. Availability flexibility, per-window limits and employee work-agreement daily/weekly limits are enforced at recommendation and final selection.
9. TP1 and TP3 validate employee/company ownership, years, finite non-negative values, row limits, immutability and evidence fields.
10. Employer-contribution journal creation no longer references an uninitialised variable and validates company accounts.
11. Direct statutory overrides remain approval-free as required, while submitted payroll/submission evidence remains immutable.
12. Installer setup fails safely if reserved Salary Component, Salary Structure or Print Format names conflict with incompatible existing data.
13. Automatic casual Salary Structure Assignments use the later of payroll start and employee joining date.
14. Reminder jobs now isolate recipients by company and roster opening period.

## Automated test result

```text
56 passed
```

Coverage categories:

- EPF, SOCSO/SKBBK and EIS table lookups and data checksums;
- PCB normal/additional remuneration examples;
- ordinary, part-time, overtime, rest-day and public-holiday pay;
- capped automatic time, breaks, overnight work and invalid numeric input;
- availability windows, shift overlap and work-hour limits;
- LHDN, EPF and PERKESO exporter shape and validation;
- statutory snapshot validation;
- permissions, POST-only mutations, payroll hooks and idempotency source contracts;
- custom DocType JSON consistency;
- runtime, installer and managed-master-data release contracts.

## Static/release checks

- Python compilation: pass
- JSON parsing: pass
- JavaScript syntax: pass
- Internal import/hook/API target resolution: pass
- Statutory source checksums: pass
- Release file-manifest verification: pass
- Cache/bytecode exclusion: pass

## Mandatory live tests still outstanding

1. Install and migrate twice on a disposable Frappe/ERPNext/Frappe HR v16 site using Python 3.14 and Node 24.
2. Exercise permissions with two companies, two employees, two roster managers and a payroll administrator.
3. Run concurrent payroll-generation requests from separate workers and verify one-row ownership.
4. Complete roster application through Shift Assignment, Employee Checkin, Attendance, Shift Work Record, Additional Salary, Payroll Entry and submitted Salary Slip.
5. Test corrections, cancellations, adjustments and failed queue retries.
6. Reconcile employer Journal Entries against Frappe HR payroll accounting and the configured Chart of Accounts.
7. Upload generated files to the employer's LHDN, KWSP and PERKESO test/production portals and retain acceptance evidence.
8. Run at least two parallel payroll periods and obtain accountable Malaysian payroll/compliance sign-off.

## Known functional boundary

RC3 validates and expires manually created standby records. It does not yet generate and cascade standby offers automatically. All annual tax/employment forms other than the explicitly versioned monthly machine files are preparation records and must be checked against current official requirements.

## RC3 addendum — 29 July 2026

A second environment and authority-format review found additional release blockers:

1. The legacy EPF CSV header was corrected from `Wages` to `Salary`.
2. EPF discontinued e-Caruman; the legacy exporter is now disabled by default, explicitly UAT-only, never portal-ready and cannot be marked officially submitted.
3. Migrations no longer overwrite reviewed statutory component flags or silently adopt unmanaged reserved components.
4. Roster skill requirements now use Frappe HR's standard Employee Skill Map for recommendation and final selection.
5. Portal error messages are escaped before display.
6. JSON duplicate-key and Jinja print-format parser tests were added.
7. A real-host Bench installation and HTTP-smoke harness was added.
8. The employee portal modal now uses Frappe v16's Bootstrap 4 jQuery API, with a guarded Bootstrap 5 fallback.
9. Split-shift opt-in and selection now follow Frappe HR's standard multiple same-date Shift Assignment setting.

A live ERPNext server still could not be started in the sandbox; see `docs/LIVE_ERPNext_TEST.md`.
