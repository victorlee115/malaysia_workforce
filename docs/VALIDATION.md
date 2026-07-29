# Validation and go-live gates

## Automated checks included

```bash
pytest -q
python -m compileall -q malaysia_workforce
npm run check:js
python scripts/verify_release.py
```

Expected pure/static-test result for 1.0.0-rc.4: **56 passed**.

The PCB suite reproduces the bundled official worked-example targets:

- January: RM110.00
- February: RM110.00
- March with TP1 relief: RM108.20
- April with additional remuneration: RM833.70

The exporter suite checks LHDN record lengths, PERKESO 278-character lines, the official legacy EPF header (`Salary`) and fail-closed EPF production controls. Source-table hashes are checked against the manifest.

## Live v16 test matrix

Run on a disposable/staging Frappe v16 site:

1. Fresh install and migrate.
2. Repeat migrate to prove idempotency.
3. Company and account setup.
4. Employee profile, agreement and coverage creation.
5. Open roster and exact-hour application from a website user.
6. Manager selection with both consent modes.
7. Shift Assignment and work-record creation.
8. Mobile IN/OUT, duplicate tap, missing OUT and correction.
9. Ordinary/additional/overtime/rest-day/public-holiday pay.
10. Weekly and monthly pay-run true-up.
11. Not Applicable statutory treatment without approval.
12. Pending Review payroll block.
13. Salary Slip submit/cancel/recalculate behaviour.
14. Employer contribution Journal Entry and cancellation.
15. LHDN, EPF and PERKESO file generation.
16. Submission rejection and next revision.
17. Payment and reconciliation.
18. Employee/manager cross-company permission isolation.
19. Backup and restore.
20. Upgrade/migration from a prior app version.

## Parallel payroll

Run at least two complete payroll periods in parallel with the existing payroll system. For every employee reconcile:

- gross earnings and each pay band;
- scheme-specific wage bases;
- employee and employer EPF;
- SOCSO, LINDUNG/SKBBK and EIS;
- PCB, TP1, TP3, zakat and CP38;
- net pay and bank file totals;
- employer Journal Entry and payable accounts;
- authority-file headcount and totals.

Include low/high wages, age/citizenship categories, multiple pay runs, new joiners, leavers, bonus, arrears, unpaid leave, part-timers, casuals, no-wage months, multiple employment and manual exclusions.

## Authority acceptance

Before production:

- validate LHDN file with the current authorised test/portal process;
- obtain or implement a verified current i-Akaun (Employer) EPF schema; the bundled legacy e-Caruman CSV is UAT-only and disabled by default;
- validate PERKESO combined file with ASSIST;
- confirm preparation forms and annual outputs against the current official requirements;
- retain screenshots/acknowledgements and test reference numbers.

## Sign-off gates

Production activation requires signed approval by:

- payroll owner;
- HR owner;
- finance owner;
- IT/security owner;
- Malaysian payroll/tax adviser or accountable compliance owner.

Do not enable automatic employer Journal Entries or automatic final-run file generation until their respective gates pass.
