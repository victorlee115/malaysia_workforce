# Isolated ERPNext/Frappe end-to-end test report

Test date: 2026-08-12  
Verdict: MariaDB and Chrome staging acceptance passed; external production gates remain

## Tested stack

- Frappe 16.19.0 (`ba18090b141740e75d52aa97bfc525ff2f831f6c`)
- ERPNext 16.20.0 (`ff46d20b259a2d65a7ded959df9f9a42991a3562`)
- HRMS 16.7.1 (`fe9ad9d362406a1ec3f394e14f6b3d5684c79b83`)
- Malaysia Workforce 1.0.0rc7 from the working tree
- Python 3.14.7, Node 24.14.0 and Yarn 1.22.22
- MariaDB 11.4.12, `REPEATABLE-READ`, `utf8mb4` / `utf8mb4_unicode_ci`
- Clean disposable MariaDB site: `mw-mariadb.localhost`

MariaDB ran in an isolated Alpine Lima VM with only the scoped site database/user exposed to the disposable bench. No Frappe, ERPNext or HRMS source was changed; all three dependency repositories remained clean after testing.

## Automated and live results

| Check | Result |
| --- | --- |
| Clean Frappe, ERPNext, HRMS and app installation | Passed |
| Consecutive MariaDB migrations / idempotency | Passed |
| Malaysia Workforce asset build | Passed |
| Pure statutory, staffing and control tests | 62 passed |
| Complete live app suite on MariaDB | 8 passed |
| Pinned-stack diagnostic | Passed |
| Statutory source-file hashes | Passed |
| Production release without activation evidence | Correctly blocked |

The live operational suite exercised a standard approved Staffing Plan, managed Shift Type reuse, submitted Shift Assignments, signed and duplicate kiosk events, standard Employee Checkins and Attendance, an immutable Shift Work Record and standard Payroll Entry/Salary Slip processing. The payroll run produced Malaysian EPF, SOCSO, EIS and PCB deductions plus an idempotent generic UAT bank CSV for one employee with a RM52.05 control total.

It also exercised invalid kiosk signatures, unsupported Sabah scope, expired statutory-review rejection, company activation gating, PERKESO/DOSH tasks, retry-safe exceptions, company/employee permissions and self-approval prevention.

## Chrome acceptance

Chrome was connected and used directly; Browser and Computer fallbacks were not needed.

- Employee, mobile 390 × 844: opened the native Casual Availability Web Form, copied a previous cycle, confirmed, reviewed the shifted windows, entered a note, submitted and returned to a list that did not disclose the Employee link.
- Outlet manager, desktop: opened the native Workspace and Staffing Plan, moved through `Collecting Availability → Proposed → Approved`, generated two assignments at 100% coverage and opened the standard HRMS `/hr/roster` view.
- Payroll processor: opened the standard Payroll workspace, Payroll Entry list and native new-entry form using the separated custom role.
- HR Manager releaser: opened the submitted Payroll Entry read-only, saw only the relevant `Release Payroll` action, confirmed it and received the intentional company-activation block.
- Auditor: opened the submitted Payroll Entry without a permission dialog, Save control, bank preparation action or release action.

The run found and fixed native UX defects in availability Web Form initialization/table copying, Employee identity exposure in the Web Form list, standard Payroll Entry role access and the HRMS read-only bank-entry probe.

## Remaining production gates

The code is a staging/UAT candidate, not an activated production payroll system. These external gates remain mandatory:

- Configure and validate the actual bank-specific adapter; the generated generic CSV is explicitly UAT-only.
- Validate LHDN, EPF i-Akaun, PERKESO/ASSIST and HRD Corp handoffs and retain authority acknowledgements.
- Run two consecutive parallel payroll periods plus an off-cycle or year-boundary case with zero unexplained differences.
- Complete multi-worker concurrency, scheduler/queue retry, physical-kiosk offline/revocation and reverse-proxy monitoring drills.
- Complete backup encryption, restoration evidence, security review and incident/exception exercises.
- Exercise standard HRMS recruitment, onboarding, leave, claims, performance, training and separation for the deployment configuration.
- Obtain Malaysian payroll/employment specialist and accountable employer sign-off.

The company activation checklist intentionally keeps bank payment, authority submission and automatic production processing disabled until this evidence exists.
