# API reference

All endpoints use the current Frappe session or Frappe token authentication and enforce linked Employee/company/role permissions. POST endpoints require CSRF protection for browser sessions.

## Employee roster

- `malaysia_workforce.api.roster.get_employee_dashboard`
- `malaysia_workforce.api.roster.get_roster_details`
- `malaysia_workforce.api.roster.submit_application` (POST)
- `malaysia_workforce.api.roster.withdraw_application` (POST)
- `malaysia_workforce.api.roster.respond_to_selection` (POST)

`submit_application` accepts JSON availability windows containing `available_from`, `available_until`, preference and optional duration/flexibility fields.

## Manager roster

- `malaysia_workforce.api.roster.manager_roster`
- `malaysia_workforce.api.roster.recommend`
- `malaysia_workforce.api.roster.select_employee` (POST)
- `malaysia_workforce.api.roster.close_applications` (POST)
- `malaysia_workforce.api.roster.publish_roster` (POST)

## Attendance

- `malaysia_workforce.api.attendance.clock` (POST)
- `malaysia_workforce.api.attendance.submit_time_correction` (POST)
- `malaysia_workforce.api.attendance.approve_work_record` (POST)

## Statutory submission

- `malaysia_workforce.api.statutory.create_monthly_submissions` (POST)
- `malaysia_workforce.api.statutory.create_next_revision` (POST)
- `malaysia_workforce.api.statutory.generate_file` (POST)
- `malaysia_workforce.api.statutory.mark_submitted` (POST)
- `malaysia_workforce.api.statutory.mark_accepted` (POST)
- `malaysia_workforce.api.statutory.mark_rejected` (POST)
- `malaysia_workforce.api.statutory.mark_paid` (POST)
- `malaysia_workforce.api.statutory.reconcile` (POST)
- `malaysia_workforce.api.statutory.generate_year_end` (POST)

## Employee declarations

- `malaysia_workforce.forms.service.employee_submit_tp1` (POST)
- `malaysia_workforce.forms.service.employee_submit_tp3` (POST)

## Example

```bash
curl -X POST \
  -H 'Authorization: token API_KEY:API_SECRET' \
  -H 'Content-Type: application/json' \
  https://erp.example.com/api/method/malaysia_workforce.api.roster.submit_application \
  -d '{
    "roster": "MW-ROS-2026-00001",
    "availability_windows": [
      {"available_from":"2026-08-15 10:00:00","available_until":"2026-08-15 15:00:00"},
      {"available_from":"2026-08-15 18:00:00","available_until":"2026-08-15 22:00:00"}
    ],
    "commitment_type":"Ask me to confirm exact hours"
  }'
```

Do not expose API secrets in mobile JavaScript. Use the authenticated Frappe session for the bundled portal.
