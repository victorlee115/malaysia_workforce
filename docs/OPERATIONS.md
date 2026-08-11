# Operations

## Staffing lifecycle

1. Manager maintains an effective-dated coverage template and creates a two-week Staffing Plan.
2. **Open Availability** generates dated demand and opens the native Web Form cycle.
3. Casual/part-time employees submit exact availability windows; missing submissions mean unavailable.
4. **Generate Proposal** favours critical coverage and longer continuous assignments, then priority and fairness.
5. Manager resolves gaps and evidenced exceptions through standard Assignment/ToDo and Workflow.
6. **Approve and Publish** creates ordinary submitted Shift Assignments and routes the manager to the HRMS roster.
7. The signed kiosk creates standard Employee Checkins; HRMS auto-attendance creates Attendance.
8. A submitted Attendance plus check-in evidence drives the immutable derived Shift Work Record.

Do not delete a confirmed assignment or derived work record to hide a change. Cancel through standard records and preserve the audit trail.

## Payroll lifecycle

1. Create and save the standard Frappe HR Payroll Entry.
2. Select company, period, frequency, payroll date, cost centre and payable account; mark the final contribution-month payroll when applicable.
3. Use **Malaysia Controls → Prepare Malaysia Inputs** to validate and reserve approved work records.
4. Resolve all validation errors.
5. Generate idempotent Additional Salary rows.
6. Review and submit Salary Slips through the standard Frappe HR flow.
8. The app calculates month-to-date statutory totals and stores a frozen snapshot on each Salary Slip.
9. Prepare the configured bank-specific file and reconcile its control total.
10. An HR Manager records the human Payroll Entry release; self-approval is not permitted.
11. Generate statutory preparation files and record separate human portal submission/payment evidence.

A work record is assigned to one Payroll Entry. Late work must be processed through a standard off-cycle/adjustment Payroll Entry, not added silently to a frozen source.

## Weekly and multiple pay runs

Statutory calculations use the current month total less amounts already submitted in earlier pay runs. Mark the correct Payroll Entry as the final contribution-month payroll. The final entry carries the balancing statutory amount.

## Monthly filing

For each authority submission:

1. Load lines from submitted Salary Slip snapshots.
2. Resolve blocking validation errors.
3. Generate the private file.
4. Verify the filename, checksum, employee count and totals.
5. Confirm the linked Payroll Entry has been human-released, then upload through the official portal or approved API.
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
- no generated payroll work record without a Payroll Entry owner;
- no generated authority file without a checksum;
- all accepted submissions have acknowledgements and all paid submissions have receipts.
- HRD Corp headcount/levy tasks and workplace-incident 48-hour tasks are not overdue.

## Backups and retention

Back up database and files before every payroll finalisation, migration and statutory revision. Verify encryption and record backup evidence/timestamp; Payroll Entry release requires a verified backup no older than 24 hours. Perform and record a restoration test at least every 90 days. Retain submitted snapshots, generated files, acknowledgements, receipts and treatment history according to your legal-retention policy.
