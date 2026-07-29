# Release validation report

**Release:** 1.0.0-rc.4  
**Validation date:** 2026-07-29  
**Target:** Frappe 16 / ERPNext 16 / Frappe HR 16 / Python 3.14 / Node 24

## Completed in this build environment

- 56 pure calculation, exporter, template, JSON, validation and source-contract tests passed.
- Every Python source file compiled successfully.
- Every JSON file parsed successfully and custom DocType field contracts were checked.
- Every JavaScript file passed `node --check` using the available Node 22 parser; runtime metadata requires Node 24 for the target bench.
- Internal Python imports, hook targets, scheduler targets, patch modules and JavaScript API targets resolved statically.
- Statutory source-table hashes matched `source_manifest.json`.
- Release metadata and file-manifest checks passed.
- Generated cache files, bytecode and test caches were removed from the release archive.

## Security and correctness defects corrected during the audit

The earlier source was not accepted unchanged. RC3 includes the RC2 corrections and additionally addresses:

- a legacy EPF CSV header mismatch (`Wages` instead of the guide's `Salary`);
- the retired e-Caruman serializer being mislabelled as a current i-Akaun schema;
- migration overwriting administrator-reviewed statutory wage classifications;
- unmanaged Salary Components being silently adopted under reserved names;
- roster `required_skill` fields not being enforced against Frappe HR's standard Employee Skill Map;
- unescaped server error messages in portal notification dialogs;
- missing duplicate-key JSON and Jinja template syntax tests.
- Bootstrap 5-only modal calls in the employee portal even though Frappe v16 ships Bootstrap 4.6.
- split shifts being offered even when Frappe HR would reject multiple same-date Shift Assignments.

RC2 had already corrected cross-company roster access, duplicate payroll claiming, premature statutory finalisation, unapproved time payment, Shift Assignment conflicts, malformed snapshot handling, employer-journal failures, TP1/TP3 validation, exporter numeric/encoding controls and unsafe master-data collisions.

See `docs/CODE_AUDIT_AND_TEST_REPORT.md` for detail.

## Statutory calculation checks

The suite includes the bundled LHDN PCB worked-example targets:

| Case | Expected | Result |
|---|---:|---:|
| January normal remuneration | RM110.00 | Pass |
| February cumulative | RM110.00 | Pass |
| March with TP1 relief | RM108.20 | Pass |
| April with bonus/additional remuneration | RM833.70 | Pass |

It also checks EPF, SOCSO/LINDUNG and EIS schedule lookups, pay-band calculations, LHDN record lengths, legacy EPF CSV constraints, PERKESO 278-character records, Jinja syntax, duplicate JSON keys, invalid numeric input and malformed statutory snapshots.

## Not completed in this build environment

No operational Frappe/ERPNext/HRMS bench, MariaDB/PostgreSQL, Redis worker, browser or authority test account was available. Consequently, RC3 is **not represented as production-certified**. The following remain mandatory on the customer's staging environment:

- fresh installation and repeated migration on the exact v16 deployment;
- live permission tests with at least two companies and separate employees/managers;
- database concurrency tests with multiple workers;
- end-to-end roster, check-in, attendance, Additional Salary, Payroll Entry, Salary Slip and Journal Entry testing;
- scheduler, queue retry and cancellation testing;
- browser/PWA and mobile-device testing;
- portal acceptance of LHDN, EPF and PERKESO files;
- parallel payroll and Malaysian payroll-practitioner sign-off;
- security review using the deployment's authentication, reverse proxy and retention settings.

## EPF production block

The old e-Caruman CSV serializer is retained only to support isolated comparison/UAT. It is disabled by default, uses schema identifier `KWSP-ECARUMAN-LEGACY-CSV-UNVERIFIED`, is never marked portal-ready and cannot be recorded as an official submission. A current verified i-Akaun adapter remains a production gate.

## Known RC3 boundaries

The standby DocType, permissions, validation and expiry job are present. Automatic sequential creation of standby offers and cascading to the next worker after decline/timeout are not implemented in RC3 and must not be described as operational until added and live-tested.

## Release decision

RC3 is approved only as a **staging/UAT release candidate**. Production use requires every gate in `docs/VALIDATION.md` to pass.
