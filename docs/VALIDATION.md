# Validation and go-live

## Automated gates

- pure EPF, SOCSO/LINDUNG, EIS, PCB, HRD, exporter, rule-data and wage tests;
- Python/JSON/JavaScript/static release checks;
- clean install and repeated migration on the pinned MariaDB stack;
- standard Payroll Entry → Salary Slip live scenario with submit-time readiness validation;
- unsupported-company, incomplete-employee, expired-rule and filing-source-change rejection;
- TP1/TP3/CP38 and same-month/year-to-date behaviour;
- Overtime Slip → Additional Salary integration;
- EPF/PERKESO/LHDN/HRD filing preparation and reconciliation;
- Employee, HR Manager, payroll processor, Accounts Manager and Auditor permission isolation;
- Chrome desktop/mobile usability for each role.

## Business acceptance

Run at least two parallel monthly payrolls plus one off-cycle or year-boundary case. Include low/high wages, age boundaries, same-month additional remuneration, joiners with TP3, TP1 reliefs, CP38, zakat, part-time, unpaid/incomplete month, overtime, rest day, public holiday and final pay.

For every employee, reconcile gross, each employee deduction, employer contribution and net pay. For every authority, reconcile employee rows and totals. Zero unexplained differences are allowed.

Validate every generated file against the current official upload validator or staging portal. Test amended/rejected submissions and preserve evidence.

## Operational acceptance

Test Company/User Permission isolation, the organisation's normal Frappe/ERPNext maker-checker approvals, backups and full restore, private file access, monitoring, failure recovery and documented month-end handoff. Train each role using `USER_GUIDE.md`.

## Production gate

Production activation requires all automated gates, clean official-stack installation, parallel payroll acceptance, external authority UAT, security/recovery drills and written Malaysian payroll-specialist sign-off. A release note or a successful calculation alone is insufficient.
