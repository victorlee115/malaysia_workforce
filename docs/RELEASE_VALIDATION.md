# Release validation report

**Release:** 1.0.0-rc.7

**Validation date:** 2026-08-12

**Target candidate:** Frappe 16.19.0 / ERPNext 16.20.0 / HRMS 16.7.1 / Python 3.14 / Node 24 / MariaDB 11.4

## Completed

- All Python sources compiled, all checked JavaScript passed syntax validation and the pure suite passed 62 tests.
- A clean MariaDB site installed the exact pinned framework apps followed by Malaysia Workforce.
- The complete live app suite passed eight tests on MariaDB 11.4.12.
- Two consecutive migrations, the app asset build and pinned-stack diagnostics passed.
- MariaDB was verified as `REPEATABLE-READ` with `utf8mb4` / `utf8mb4_unicode_ci`.
- Dependency repositories remained clean; the app uses hooks, custom fields, fixtures and standard client extensions only.
- Chrome acceptance passed for employee, outlet manager, payroll processor, HR Manager releaser and auditor roles.
- A standard Payroll Entry produced and submitted a standard Salary Slip with Malaysian statutory deductions and an idempotent UAT-only bank artifact.
- Human release correctly stopped at the unsigned company production-activation gate.
- Statutory source-table hashes matched `source_manifest.json`.

See `ISOLATED_E2E_TEST_REPORT.md` for role-by-role evidence and exact environment details.

## RC7 architecture and controls

RC7 keeps standard Frappe HR authoritative and removes the former duplicate roster and payroll-run surfaces. Malaysia Workforce now supplies only native availability, coverage planning, deterministic casual allocation, Malaysian rules and evidence/release controls around standard Shift Assignment, Employee Checkin, Attendance, Payroll Entry and Salary Slip records.

Separated standard permissions let payroll processors operate Payroll Entry while releasers and auditors remain read-only. Client actions mirror the server roles: processors prepare Malaysia inputs and bank files; HR Managers release and reconcile; auditors receive no mutating action. Frappe's own submitted-document probe is skipped for read-only viewers instead of granting them unsafe submit permission.

The availability and Staffing Plan screens use standard Frappe Web Form, Desk Form, Workflow, List View, Workspace and Query Report patterns. Published schedules are ordinary HRMS shifts and are viewed in the normal HRMS roster/PWA.

## Statutory calculation checks

The Python 3.14 suite passes the bundled LHDN PCB worked-example targets:

| Case | Expected | Result |
| --- | ---: | --- |
| January normal remuneration | RM110.00 | Pass |
| February cumulative | RM110.00 | Pass |
| March with TP1 relief | RM108.20 | Pass |
| April with bonus/additional remuneration | RM833.70 | Pass |

The suite also checks EPF, SOCSO/LINDUNG, EIS, HRD levy, minimum wage, flexible-worker pay boundaries, TP1 controls, effective dates, statutory record constraints, malformed snapshots and invalid numeric input.

## External production blocks

No production bank or employer authority credentials can be selected from repository context. Company activation therefore rejects the generic UAT CSV and requires an installed bank-specific adapter plus acceptance evidence. EPF uses a current i-Akaun preparation worksheet; the retired e-Caruman artifact remains UAT-only.

Foreign workers, Sabah, Sarawak and unsupported PCB regimes fail closed. Full-time/monthly payroll remains standard Frappe HR; custom flexible-work pay is limited to reviewed hourly part-time/casual agreements.

Production still requires bank/authority UAT, two parallel payroll periods, an off-cycle or year-boundary simulation, recovery/security/concurrency drills, the configured standard HRMS lifecycle tests and specialist sign-off.

## Release decision

RC7 is approved as a **MariaDB-tested staging/UAT release candidate**. It is not production activated until every gate in `VALIDATION.md` and the signed Company activation checklist passes.
