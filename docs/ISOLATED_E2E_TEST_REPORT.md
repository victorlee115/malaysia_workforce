# Isolated ERPNext/Frappe end-to-end test report

**Test date:** 2026-08-13

**Verdict:** Existing-site MariaDB integration and the exercised Chrome role screens pass, including employee TP1/TP3 submission. Production release remains blocked by the external and clean-stack gates below.

## Environment

- Frappe 16.31.0 (`6a329d068416768ec47ccd3326b9cc95a8d7bf99`)
- ERPNext 16.31.1 (`22247ab7c57ab51b5e05c274e85321402d133a64`)
- HRMS 16.16.0 (`f281e8b172ac8836ad89c59df65a922101103097`)
- Malaysia Workforce 1.0.0rc11 from the working tree
- Python 3.14.7, Node 24 and MariaDB 11.4.12
- Isolated site: `mw-mariadb.localhost`

MariaDB ran in a disposable Lima environment. The app was tested as an extension of the standard Frappe, ERPNext and HRMS records; no dependency source was patched or monkey-patched.

## MariaDB workflow evidence

The existing test site migrated twice consecutively without error. The live scenarios exercised:

- standard Company, Employee, Contract, Salary Component, Salary Structure Assignment, Additional Salary, Overtime Slip, Payroll Entry and Salary Slip records;
- gross pay of RM6,000 and net pay of RM5,053.70 with deterministic EPF, SOCSO, LINDUNG 24 Jam, EIS, PCB, CP38, zakat and HRD calculations;
- two-hour full-time overtime producing RM72.12 and six hours of part-time additional work producing RM70.00;
- TP1, TP3 and CP38 payroll inputs;
- standard Payroll Entry submit-time readiness validation without a parallel release lifecycle;
- retry-safe EPF, PERKESO, LHDN and HRD Corp preparation files, employee/control totals, human evidence and reconciliation state;
- source-change protection on filing: an unchanged retry returned the same artifact, while changed statutory results and serialized employee identities were detected;
- employee/company permission isolation, read-only Auditor access and server-side rejection of cross-company payroll report filters;
- calendar-month aggregation of non-overlapping Overtime Slips against the 104-hour limit;
- fail-closed earning classification, LINDUNG release windows/multiple-employer scope, HRD headcount, signed TP3 evidence and CP38 remaining-balance checks;
- employee TP1/TP3 save → Pending Review, retry safety, native HR approval and two distinct prior-employer TP3 records;
- removal of the former roster, availability, employee-profile, work-agreement, shift-work-record and parallel payroll-run DocTypes.

The synthetic authority receipt and activation attachment prove application state transitions only. They are not evidence of acceptance by an authority or bank.

## Chrome acceptance by role

Chrome was used directly; Browser and Computer Use fallbacks were not needed.

### Employee

- Signed in as the native `Employee Self Service` user and opened the actual Frappe HR PWA at `/hrms` at 390 × 844. A narrow Desk page was not treated as mobile acceptance.
- Clicked Home, Attendance, Leaves, Expenses, Salary and Profile, plus new Attendance Request, Shift Request, Leave Application, Expense Claim and Employee Advance forms. Every screen rendered without a fresh browser error.
- Opened the Shift Type, Leave Type, Expense Approver and Currency selectors without permission failures.
- Viewed the standard 2026 Payroll Period, year-to-date amount and three own submitted Salary Slips through the unmodified HRMS PWA.
- Downloaded a submitted Salary Slip PDF through the native HRMS action; the app selected Frappe's native headless-Chrome renderer because the isolated host did not have `wkhtmltopdf` installed.
- Opened TP1 and TP3 through direct standard Web Form links; the employee has no custom portal or Desk Workspace.
- Created TP1 and TP3 with Employee and Company derived from the signed-in active Employee on the server, and tax year/currency defaulted without exposing those identities for editing.
- Verified that a new TP1 begins with no misleading relief row and shows relief code, amount, claim month and receipt in the native child table.
- Selected **Send for Review** on TP1 and TP3 and received the native **Sent for Review** success page; both records reached Pending Review.
- Verified both tax forms at 390 × 844 with no page-level horizontal overflow and verified labelled native response lists.
- Opened a standard submitted Salary Slip, including its ordinary deductions and Malaysia calculation audit.
- Confirmed the mobile page width remained 390 px with no page-level horizontal overflow.

### HR Manager

- Used `Statutory Details` on the standard Employee form.
- Used `Statutory Working Terms` on the standard Contract form; no parallel employee profile or work agreement exists.
- Reviewed TP1 evidence and maintained a CP38 directive.
- Opened the employee-created Pending Review TP1, saw only the native **Approve** and **Return** actions, and received Frappe's standard confirmation dialog. A duplicate annual TP1 approval was correctly blocked; the live MariaDB scenario proved the valid TP3 approval path.
- Used the native Workspace and standard record navigation.

### Payroll processor

- Opened a standard Payroll Entry and selected the direct, read-only `Check Statutory Setup` action.
- Saw only standard Payroll Entry fields; the app adds no status, release or visible hash fields.

### Statutory operator

- Prepared an EPF filing from a standard Frappe form as Accounts Manager.
- Verified employee rows, wage/contribution totals and the private standard File attachment. Internal hashes were hidden from the form.
- Did not claim an external submission; the UI requires human evidence before submission/reconciliation states.

### Auditor

- Opened Payroll Entries, Salary Slips, TP1/TP3/CP38 records, filings and reports read-only.
- Saw no Save, Prepare, Submit or Reconcile action.

### System Manager

- Configured `Statutory Payroll` on the standard Company form without losing native sections.
- Verified employer identifiers, jurisdiction and HRD status are grouped in the standard form.

The complete employee PWA retest produced no fresh browser-console errors. Earlier Desk tabs retained Socket.IO polling noise because the disposable test web process did not run the realtime service; those entries predated the PWA retest and are not application exceptions. The optional notification-relay endpoint was also absent from this minimal process. A full production Bench must run its normal web, realtime, worker and scheduler services.

## Clean-site blocker

A brand-new site could not reach Malaysia Workforce installation. Pinned Frappe 16.31.0 failed during its own bootstrap with:

```text
MySQLdb.OperationalError: (1054, "Unknown column 'protect_attached_files' in 'INSERT INTO'")
```

The pinned framework's DocType model includes `protect_attached_files`, but its bootstrap SQL does not create that column before the insert. The current official version-16 revision tested was the same commit. The app deliberately does not patch Frappe core to conceal this issue.

## Remaining production gates

- Retest a completely clean official stack after Frappe publishes a compatible build.
- Validate every EPF, PERKESO, LHDN and HRD file against the current official portal or validator.
- Run two consecutive parallel payroll months and an off-cycle or year-boundary payroll with zero unexplained differences.
- Complete multi-worker concurrency, scheduler, backup restore, security and private-file drills.
- Obtain Malaysian payroll specialist and accountable employer sign-off.

Until these gates pass, this is an evidence-backed staging/UAT candidate, not production-ready payroll.
