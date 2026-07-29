# Operations

## Casual roster lifecycle

1. Manager creates a Draft roster and coverage rows.
2. Manager opens applications.
3. Eligible workers submit exact availability windows.
4. Manager reviews coverage by date, role and interval.
5. Manager selects a worker and an exact subset of offered hours.
6. If employee confirmation is required, the worker accepts or declines in `/workforce`.
7. Publishing creates a standard submitted Shift Assignment and a Shift Work Record.
8. Employee clocks IN and OUT or a device integration creates Employee Checkin rows.
9. Normal records are verified; exceptions request employee correction or manager review.
10. An Approved Shift Work Record becomes eligible for payroll.

Do not delete a confirmed assignment to hide a cancellation. Use the roster/selection status and preserve the audit trail.

## Payroll lifecycle

1. Create a Malaysia Payroll Run.
2. Select company, period, frequency, payroll date, cost centre and payable account.
3. Collect and validate approved, unowned work records.
4. Resolve all validation errors.
5. Generate idempotent Additional Salary rows.
6. Create the standard Payroll Entry.
7. Review and submit Salary Slips through the standard Frappe HR flow.
8. The app calculates month-to-date statutory totals and stores a frozen snapshot on each Salary Slip.
9. If configured, create the employer contribution Journal Entry.
10. On a final pay run, generate monthly statutory submissions/files automatically.

A work record is assigned to one payroll run. Late work must be processed through an adjustment run, not added silently to a frozen run.

## Weekly and multiple pay runs

Statutory calculations use the current month total less amounts already submitted in earlier pay runs. Mark the correct run as `is_final_run_for_month`. The final run carries the balancing statutory amount and is the normal trigger for monthly files.

## Monthly filing

For each authority submission:

1. Load lines from submitted Salary Slip snapshots.
2. Resolve blocking validation errors.
3. Generate the private file.
4. Verify the filename, checksum, employee count and totals.
5. Upload through the official portal or approved API.
6. Record the official external reference and attach acknowledgement.
7. Mark accepted or rejected.
8. Record payment reference, amount, receipt and date.
9. Reconcile; the difference must be within RM0.01.
10. For rejection/correction, create the next revision rather than changing the submitted source.

`Generated` or `Ready for Portal` is not the same as `Submitted`.

## Year end

Generate annual preparation statements only after the final December payroll and all amendments are submitted. Reconcile EA/EC employee totals, CP8D/Form E preparation data, monthly PCB submissions and general ledger totals. Confirm official deadlines and current portal specifications for that tax year.

## Daily operational checks

- background workers and scheduler healthy;
- no pending check-in exceptions approaching payroll cut-off;
- no expired work/statutory profile;
- no statutory treatment left `Pending Review`;
- no rate below the active minimum;
- no payroll work record without a run owner after generation;
- no generated authority file without a checksum;
- all accepted submissions have acknowledgements and all paid submissions have receipts.

## Backups and retention

Back up database and files before every payroll finalisation, migration and statutory revision. Retain submitted snapshots, generated files, acknowledgements, receipts and treatment history according to your legal-retention policy.
