# API reference

The normal employee and manager experience uses standard Frappe Forms, Workflow, Web Forms and Frappe HR screens. Custom endpoints exist only where Frappe HR has no equivalent.

## Availability helpers

- `...casual_availability.availability_context` — returns the logged-in Employee and open cycle for the native Web Form.
- `...casual_availability.previous_availability_windows` — returns the prior 14-day windows for confirmed copying.

Availability is persisted as `Casual Availability`; there are no application, selection, swap or custom-roster APIs.

## Signed kiosk

- `malaysia_workforce.api.attendance.set_kiosk_credential` (POST; HR manager)
- `malaysia_workforce.api.attendance.kiosk_clock` (POST; kiosk integration identity)

`kiosk_clock` accepts `event_id`, registered `kiosk_id`, `employee`, PIN/QR credential, `IN`/`OUT`, device timestamp, HMAC-SHA256 signature and `offline_queued`. The signed payload is:

```text
event_id|kiosk_id|employee|log_type|device_timestamp
```

The endpoint creates a standard `Employee Checkin`. A duplicate event ID returns the existing record. It does not create custom attendance.

## Attendance exceptions

- `malaysia_workforce.api.attendance.submit_time_correction` (POST)
- `malaysia_workforce.api.attendance.review_time_correction` (POST; different approver)
- `malaysia_workforce.api.attendance.approve_work_record` (POST; different approver)

Corrections use evidenced standard `Employee Checkin` rows. A submitted standard `Attendance` record is required before the derived work/pay record can be submitted.

## Payroll controls

- `malaysia_workforce.payroll.services.prepare_payroll_entry` (POST)
- `malaysia_workforce.banking.service.prepare_bank_file` (POST)
- `malaysia_workforce.banking.service.release_payroll` (POST; HR Manager releaser)
- `malaysia_workforce.banking.service.reconcile_bank_file` (POST)
- `malaysia_workforce.compliance.activation.activate_company` (POST)
- `malaysia_workforce.compliance.activation.deactivate_company` (POST)

The standard `Payroll Entry` is the sole control owner. Bank adapters are supplied through the `malaysia_workforce_bank_adapters` hook and must return deterministic content, filename and a control total equal to submitted Salary Slip net pay.

## Statutory submissions

- `malaysia_workforce.api.statutory.create_monthly_submissions` (POST)
- `create_next_revision`, `generate_file`, `mark_submitted`, `mark_accepted`, `mark_rejected`, `mark_paid`, `reconcile`, `generate_year_end` (POST)

Authority adapters validate and prepare files. They never assert success without human evidence or an approved official API response.

## Incidents and declarations

- `malaysia_workforce.compliance.incidents.record_workplace_incident` (POST)
- `malaysia_workforce.compliance.incidents.annual_incident_register` (read only)
- `malaysia_workforce.forms.service.employee_submit_tp1` (POST)
- `malaysia_workforce.forms.service.employee_submit_tp3` (POST)

Do not embed API secrets in browser JavaScript. Browser users authenticate through their normal Frappe session.
