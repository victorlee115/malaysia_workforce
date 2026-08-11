# Malaysia Workforce for ERPNext/Frappe HR

**Version:** 1.0.0-rc.7

**Pinned candidate stack:** Frappe 16.19.0, ERPNext 16.20.0, Frappe HR 16.7.1, Python 3.14, Node 24

**Licence:** GPL-3.0-or-later

Malaysia Workforce is a focused Malaysian localization and cafe-staffing layer for Frappe HR. It does not replace Frappe HR.

Standard `Employee`, recruitment, onboarding, `Shift Assignment`, `Employee Checkin`, `Attendance`, leave, claims, training, performance, `Payroll Entry`, `Salary Slip`, accounting and separation records remain authoritative. This app adds only:

- a native Web Form for casual/part-time availability;
- coverage templates and assisted two-week staffing plans that publish ordinary Shift Assignments;
- immutable derived work/pay breakdowns;
- Malaysian payroll/statutory calculations and preparation files;
- human payroll release, bank reconciliation and compliance evidence controls;
- a signed, replay-safe fixed-kiosk check-in endpoint.

There is no separate workforce portal, custom roster, parallel payroll run, design system, core fork or monkey patch.

## Native staffing flow

```text
Casual Availability (Web Form)
  → Cafe Coverage Template
  → Cafe Staffing Plan (Frappe Workflow)
  → standard Shift Type + Shift Assignment
  → signed kiosk Employee Checkin
  → standard Attendance
  → derived Shift Work Record
  → standard Payroll Entry + Salary Slip
  → bank/statutory preparation and human release
```

Employees continue to use Frappe HR self-service for published shifts, shift requests, attendance history, leave, claims and payslips. Managers return to the standard HRMS roster after approving a staffing plan.

## Staffing defaults

- 14-day cycles; availability opens 21 days before and closes seven days before.
- Availability uses 30-minute boundaries and may contain multiple windows per day.
- No submitted availability means unavailable.
- Automatic recommendations prefer continuous 4–8 hour assignments, then 2–4 hours.
- One-hour shifts are never generated automatically. A sub-two-hour manual assignment needs a reason, private employee confirmation, and an effective agreement that permits that duration; anything below one hour is rejected.
- Critical coverage and longer useful availability rank before staffing priority and fairness.
- Priority never bypasses availability, designation/skill, location, leave, conflicts or agreement hour limits.

## Malaysian scope

The candidate supports reviewed Peninsular Malaysia cases for supported Malaysian citizens/permanent residents and standard PCB treatment. Unsupported jurisdictions, worker classes, tax regimes, missing profiles and expired rule reviews fail closed.

Included controls cover EPF, SOCSO, EIS, PCB, HRD Corp levy, minimum wage, flexible-worker pay bands, deductions/final pay, employee notifications, incident escalation and current human authority handoffs. Generated worksheets are preparation records; they do not claim official submission without recorded human evidence.

## Installation

Install on an isolated staging site using the exact versions in [`compatibility-lock.json`](compatibility-lock.json):

```bash
cd /path/to/frappe-bench
bench get-app /path/to/malaysia_workforce
bench --site staging.example.com install-app malaysia_workforce
bench --site staging.example.com migrate
bench --site staging.example.com migrate
bench build --app malaysia_workforce
bench --site staging.example.com execute malaysia_workforce.diagnostics.run
```

Before payroll, configure the Company, employee work agreements/profiles, standard HRMS leave and holiday policies, an auto-attendance base casual Shift Type, Salary Structures/Assignments, accounts, kiosk and bank/authority UAT evidence. See [Configuration](docs/CONFIGURATION.md).

## Verification

```bash
pytest -q
python -m compileall -q malaysia_workforce
npm run check:js
python scripts/verify_release.py
```

Production activation remains blocked until the exact-stack clean install/upgrade suite, two parallel payrolls, an off-cycle or year-boundary simulation, bank/authority UAT, role/security review and backup restoration drill all pass with zero unexplained differences.

## Documentation

- [Installation](docs/INSTALLATION.md)
- [Configuration](docs/CONFIGURATION.md)
- [Frappe HR ownership](docs/FRAPPE_HR_CONFIGURATION.md)
- [Operations](docs/OPERATIONS.md)
- [Security](docs/SECURITY.md)
- [Statutory scope](docs/LEGAL_AND_STATUTORY.md)
- [Validation and go-live](docs/VALIDATION.md)
- [API](docs/API.md)
- [Upgrade](docs/UPGRADE.md)

This app can reduce routine HR administration; it cannot remove the employer's legal accountability or the need for periodic Malaysian payroll/employment specialist review.
