# Changelog

## 1.0.0-rc.13 — 2026-08-18

- Added the explicit `Statutory Profile` field on Employee. `SOCSO + EIS — LINDUNG Optional` keeps contractors in standard Frappe HR records while calculating only SOCSO, EIS and applicable LINDUNG.
- Excluded that profile from EPF, LHDN and HRD Corp calculations and filings, blocked tax declarations and CP38, and added profile-aware payroll readiness and filing fingerprints.
- Documented the contractor setup and monthly workflow in the beginner user guide.
- Granted HR Manager and Auditor permlevel-1 read of the Salary Slip Statutory Profile snapshot so the field is visible after payroll.
- Added a Statutory Profile column and a default-off Show All Statutory Profiles filter to Malaysia Annual Remuneration, and stopped both payroll reports from losing the profile through `get_list` field permissions.
- Rejected a direct Salary Slip submit when the saved profile snapshot no longer matches the Employee.
- Stopped HRMS `calculate_net_pay` from putting Salary Structure Zakat back onto a contractor slip at submit.
- Showed **Applicable** on the Salary Slip statutory-results grid and moved the Statutory Profile snapshot above that table.
- Filled the Company filter on payroll reports from the user's sole Company permission when no default is set, and granted System Manager read/select/report on Employee, Salary Slip and Payroll Entry so those report roles can actually run.
- Directed employees to **View Salary Slips** on HRMS home instead of the blank `/hrms/home/salary` route.

## 1.0.0-rc.12 — 2026-08-16

- Repaired upgrades from pre-lean schemas that retained permission rows for retired localization roles whose Role records no longer exist. The migration now removes only those orphaned rows before Frappe refreshes Employee Self Service permissions and still stops if a user carries a retired role.

## 1.0.0-rc.11 — 2026-08-13

- Fixed employee payslip PDF downloads on hosts without `wkhtmltopdf` by selecting Frappe v16's native headless-Chrome renderer through a narrowly scoped HRMS endpoint hook.
- Kept `wkhtmltopdf` as the first choice when the host provides it and documented production Chromium provisioning and PDF smoke testing.

## 1.0.0-rc.10 — 2026-08-13

- Completed the native employee TP1/TP3 handoff: the standard Web Form now saves the declaration and immediately applies Frappe's `Send for Review` Workflow action, with retry-safe server authorization and a clear success page.
- Derived hidden Employee and Company values from the signed-in active Employee on the server, removing browser-only mandatory-field failures without trusting client input.
- Added a narrow upgrade patch for missing TP1/TP3 Workflow submit rights while preserving unrelated administrator permission customizations.
- Supported one signed TP3 per distinct previous employer and employment period, with duplicate prevention and combined annual relief caps across every approved TP3 and the current-employer TP1.
- Added labels and field types to native Web Form lists, removing `undefined` headings.
- Added MariaDB coverage for employee submission, retry safety, HR approval and multiple previous employers, plus Chrome mobile acceptance for both tax Web Forms.

This remains a release candidate. Clean official-stack bootstrap, external authority UAT, parallel payroll, recovery/security drills and Malaysian payroll-specialist sign-off are still required before live payroll.

## 1.0.0-rc.9 — 2026-08-13

- Corrected LINDUNG 24 Jam from an opt-in election to the opt-out scheme PERKESO confirmed on 10 July 2026. Participation is now the default: an employee who has recorded nothing contributes, and the deduction stops only from the effective date of their own Liability Release Notice. The previous model blocked payroll for every employee whose participation was unrecorded, which after the rc.8 migration was all of them.
- A release cannot take effect before 8 July 2026, so already-deducted June 2026 contributions are never reversed.
- Evidence and an effective date are now required only for a recorded release, not for the default.
- Fixed a mid-month over-deduction: SKBBK was folded into the SOCSO scheme total instead of being tracked separately, so a second Salary Slip in the same month re-charged SKBBK that the first had already taken while over-reducing SOCSO. On an even RM3,000/RM3,000 September split this charged RM22.15 too much SKBBK and RM15.00 too little SOCSO, and left the PERKESO filing totals disagreeing with the payslips; the amount varies with how the month is split, up to a full band.
- Fixed the payroll-readiness live scenario, which passed its filter as `on_date` and so evaluated readiness against the current date instead of the period end.
- Enforced Company/User Permissions in payroll reports and rejected unclassified earning components before statutory calculation.
- Enforced the official existing/new-employee LINDUNG release windows and failed closed for unsupported multiple-employer selection.
- Reconciled HRD Corp registration against the Malaysian-employee threshold and excluded permanent residents from leviable employees.
- Aggregated Overtime Slip detail hours by calendar month for the 104-hour limit.
- Included employee and employer identifiers in statutory-filing fingerprints so identity changes invalidate prepared files.
- Replaced the arbitrary TP3 relief total with controlled, evidenced relief rows sharing annual limits with TP1.
- Stopped automatic legacy-role mapping from granting broader HR/accounting permissions.
- Corrected CP38 remaining-balance handling across multiple Salary Slips in one month.

**Action required on upgrade.** A migration sets every `Not Set` employee to `Participating` and clears election paperwork left on participating employees; the underlying File records are preserved on the Employee. Employees already recorded as `Not Participating` are left untouched and written to the error log, because this app cannot tell a genuine portal Liability Release Notice from an election captured under the old model — **re-verify each one before the next payroll**. Submitted Salary Slips are not recalculated: review every slip since 1 June 2026 that recorded zero LINDUNG, and any employee with two slips in one month, and correct them through the documented amendment process.

## 1.0.0-rc.8 — 2026-08-12

- Rebuilt the app as a lean Malaysian payroll localisation around standard Frappe HR records.
- Removed the custom staffing, availability, roster, kiosk, employee-profile, work-agreement, bank, incident, privacy, accumulator and parallel-payroll subsystems.
- Added a guarded migration that stops when real legacy operational records need an explicit archive or migration decision.
- Added Malaysia fields to standard Company, Employee, Contract, Salary Component, Salary Slip, Payroll Entry and Overtime Type records.
- Added effective-dated EPF, SOCSO/SKBBK, EIS, PCB, HRD Corp, minimum-wage and wage-rule calculations.
- Added TP1, TP3, CP38, statutory filing, payroll-readiness and annual-remuneration features using native Frappe forms and reports.
- Added source-hash protection, two-person payroll release and read-only auditor access.
- Added deterministic live MariaDB scenarios, including post-validation source-tamper rejection.
- Pinned the tested Frappe 16.31.0, ERPNext 16.31.1 and HRMS 16.16.0 stack.
- Recorded the upstream Frappe clean-site bootstrap defect honestly as a production release blocker.

The prior implementation remains preserved on branch `codex/archive-pre-lean-20260812` at commit `5fce234`.
