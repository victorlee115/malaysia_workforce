# Frappe HR ownership

Frappe HR and ERPNext remain authoritative.

| Need | Standard record or screen | Malaysia addition |
|---|---|---|
| Person and employment status | Employee | statutory IDs and PCB status fields |
| Legal employment terms | Contract | wage basis, hours and rest-day fields |
| Recurring pay | Salary Structure / Assignment | statutory treatment on Salary Component |
| Variable pay | Additional Salary | classified by Salary Component treatment |
| Overtime | Overtime Slip / Type | normal, rest-day and public-holiday rates |
| Monthly payroll | Payroll Entry | read-only statutory readiness check and submit-time validation |
| Employee result | Salary Slip | deductions and statutory-result table |
| Leave, attendance and lifecycle | HRMS records | no custom replacement |
| Optional reliefs | — | TP1 |
| Previous-employment tax inputs | — | TP3 |
| LHDN extra deduction | — | CP38 |
| Authority handoff | — | Malaysia Statutory Filing |

There is no separate employee profile, work agreement or payroll run. Standard Employee, Contract and Payroll Entry already provide the correct lifecycle and permission model.

Never patch Frappe, ERPNext or HRMS core. The app uses hooks, Custom Fields, the supported Overtime Slip class extension, ordinary Desk forms, reports and a Workspace.
