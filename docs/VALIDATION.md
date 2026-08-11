# Validation and go-live gates

## Automated checks included

```bash
pytest -q
python -m compileall -q malaysia_workforce
npm run check:js
python scripts/verify_release.py
```

The exact test count is intentionally not hard-coded; CI must report zero failures for the checked-out release.

The PCB suite reproduces the bundled official worked-example targets:

- January: RM110.00
- February: RM110.00
- March with TP1 relief: RM108.20
- April with additional remuneration: RM833.70

The suite checks HRD levy, minimum-wage/classification boundaries, TP1 code/cap/evidence rules, special-regime rejection, LHDN record lengths, PERKESO 278-character lines, current EPF worksheet boundaries, the UAT-only legacy serializer and source-table hashes.

## Live v16 test matrix

Run on a disposable/staging Frappe v16 site:

1. Fresh install and migrate.
2. Repeat migrate to prove idempotency.
3. Company, rule deadline, HRD Corp, privacy notice/acknowledgements, bank adapter/UAT and account setup.
4. Employee profile, agreement and coverage creation.
5. Submit and amend a 14-day Casual Availability record from the authenticated Web Form.
6. Manager selection with both consent modes.
7. Shift Assignment and work-record creation.
8. Signed kiosk IN/OUT, offline replay, duplicate ID, clock drift, revocation, missing OUT and correction.
9. Ordinary/additional/overtime/rest-day/public-holiday pay.
10. Weekly, daily, hourly and monthly standard payroll true-up, including zero-work paid days.
11. Not Applicable statutory treatment with evidence and HR Manager approval; unauthorized exclusion rejection.
12. Pending Review payroll block.
13. Salary Slip submit/cancel/recalculate behaviour.
14. Employer contribution Journal Entry and cancellation.
15. LHDN, EPF i-Akaun worksheet, PERKESO and HRD Corp generation.
16. Submission rejection and next revision.
17. Payment and reconciliation.
18. Employee/manager cross-company permission isolation.
19. Backup and restore.
20. Workplace incident escalation, annual register source and deadline tasks.
21. Backup restoration and recorded restore evidence.
22. Upgrade/migration from the current RC schema.

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
- UAT the current i-Akaun human-entry worksheet and retain portal acknowledgement; never treat it as an upload schema;
- validate PERKESO combined file with ASSIST;
- reconcile the HRD Corp levy worksheet and payment evidence;
- validate the selected bank-specific adapter and control totals;
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
