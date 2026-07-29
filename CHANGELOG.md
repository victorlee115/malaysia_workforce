# Changelog

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
