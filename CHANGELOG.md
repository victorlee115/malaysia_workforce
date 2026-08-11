# Changelog

## 1.0.0-rc.7 — 2026-08-12

- Passed clean installation, consecutive migration, asset build and the complete live app suite on MariaDB 11.4.12 with the exact pinned Frappe/ERPNext/HRMS v16 stack.
- Completed Chrome acceptance for mobile employee availability, manager proposal/publication, native HRMS roster, payroll processing, independent release and read-only audit personas.
- Fixed Web Form lifecycle/table-copy behavior, hidden employee identity in availability lists and made live scenarios retry-safe across date changes and prior payroll generation.
- Added standard Frappe permissions for separated payroll roles without granting submit rights to releasers or auditors; suppressed HRMS's mutating bank-entry probe for genuine read-only viewers.
- Completed a standard Payroll Entry and Salary Slip flow with Malaysian deductions and an idempotent generic UAT bank file, while retaining the production activation block.
- Fixed statutory Salary Slip deduction insertion and made pure tests importable by Frappe's native test discovery without a bench-only pytest dependency.

## 1.0.0-rc.6 — 2026-08-11

- Removed the custom roster portal, roster DocTypes, planner page and parallel Malaysia Payroll Run.
- Added native availability Web Form, effective coverage templates and Workflow-driven two-week Staffing Plans.
- Added deterministic long-shift-first allocation, coverage gaps, managed Shift Type reuse and standard Shift Assignment publishing.
- Enforced agreement minimums, split-shift policy and complete hard eligibility on both generated and manager-adjusted recommendations; protected adjustments with chained audit evidence and standard ToDos.
- Moved reservation, validation, human release, bank and statutory preparation controls to standard Payroll Entry.
- Added a standard read-only, explicitly Company-scoped Malaysia Workforce Auditor role and disabled self-approval for Staffing Plan publication.
- Added fail-closed legacy-schema preflight, native Workspace/report UX and updated exact-stack live scenarios.

## 1.0.0-rc.5 — 2026-08-11

- Made standard Frappe HR `Payroll Entry`, `Salary Slip`, `Shift Assignment`, `Employee Checkin`, attendance, leave, claims, training and lifecycle records authoritative; retained the old payroll run only as a read-only internal compatibility snapshot.
- Added Peninsular Malaysia and supported-citizenship fail-closed gates, effective-dated minimum wage and flexible-worker classifications, deduction/final-pay controls and reviewed part-time/rest-day/public-holiday rules.
- Added HRD Corp levy calculation, accounting, portal preparation, payment tasks, training evidence and headcount threshold alerts.
- Rebuilt TP1 validation around controlled relief codes and evidence; rejected unimplemented special PCB regimes and corrected CP21/CP22/CP22A notification handling.
- Added current EPF i-Akaun preparation while keeping retired e-Caruman output explicitly UAT-only and non-submittable.
- Added signed, idempotent kiosk events on standard Employee Checkin, replay protection, offline/drift controls and trusted-device credential rotation.
- Added production activation, source hashes, one-final-period uniqueness, human release, bank-adapter/UAT gates, reconciliation, immutable exception resolution and processor/releaser separation.
- Added company-scoped permissions, self-approval prevention, workplace-incident escalation, scheduler failure isolation and expanded readiness diagnostics.
- Pinned the certification candidate to Frappe 16.19.0, ERPNext 16.20.0, Frappe HR 16.7.1, Python 3.14 and Node 24; clean release verification now operates on Git-tracked archive inputs.

## 1.0.0-rc.4 — 2026-07-29

- Corrected the Frappe app distribution name from `malaysia-workforce` to `malaysia_workforce`.
- Ensured Bench clones the app to `apps/malaysia_workforce`.
- Fixed installation failure when Bench reads the application version.

## 1.0.0-rc.3 — 2026-07-29

- Corrected the legacy EPF CSV header to `Salary`.
- Reclassified the bundled EPF serializer as retired e-Caruman UAT-only, disabled it by default and blocked official-submission status.
- Preserved administrator-reviewed Salary Component formulas, accounts and statutory classifications during migration.
- Failed installation on unmanaged reserved Salary Component names instead of silently adopting them.
- Enforced roster skill requirements through Frappe HR's standard Employee Skill Map.
- Escaped portal error messages and added Jinja and duplicate-JSON-key tests.
- Added a deterministic live Bench installation, migration, test and HTTP-smoke harness.
- Replaced Bootstrap 5-only portal modal calls with a Frappe v16 Bootstrap 4-compatible adapter.
- Integrated split-shift availability with Frappe HR's standard multiple same-date Shift Assignment setting.
- Expanded the pure/static suite to 56 tests.

## 1.0.0-rc.2 — 2026-07-29

- Corrected the supported runtime to Frappe v16's Python 3.14 and Node 24 baseline.
- Added company and assigned-manager permission isolation for rosters and linked records.
- Added database locking, work-record reservation and idempotent payroll finalisation.
- Delayed statutory submission generation until every linked Salary Slip is submitted.
- Prevented automatic pay from including unapproved early-arrival or late-departure time.
- Added standard Shift Assignment conflict checks, overnight handling and availability limits.
- Made submitted statutory snapshot parsing fail closed and hardened authority exporters.
- Hardened TP1/TP3 validation, immutability and evidence references.
- Added finite-number, row-count, company-account and reserved-master-data validation.
- Added safe casual Salary Structure validation and mid-period joiner assignment dates.
- Expanded the pure/static suite to 46 tests and added release-integrity checks.

## 1.0.0-rc.1 — 2026-07-29

- Initial production-oriented release candidate for Frappe/ERPNext/Frappe HR v16.
- Added exact-hour casual roster applications and manager-controlled selection.
- Added employee confirmation offers, attendance, corrections and payable work records.
- Added hourly pay bands and idempotent Additional Salary/Payroll Entry integration.
- Added effective employee work agreements, Malaysian profiles and direct statutory overrides without approval.
- Added month-to-date EPF, SOCSO/LINDUNG, EIS and PCB calculations.
- Added LHDN, EPF and PERKESO monthly files with source snapshots and checksums.
- Added preparation records for TP1, TP3, employee notifications, EA/EC, CP8D and Form E.
- Added employer contribution Journal Entry, submission revisions, payment and reconciliation.
- Added 25 pure automated tests and release verification tooling.
