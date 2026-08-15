# Public methods

The normal interface is standard Frappe forms. The following whitelisted methods support native form actions:

- `malaysia_workforce.payroll.events.check_readiness(payroll_entry)` validates a draft standard Payroll Entry and returns employee-specific issues.
- `Malaysia Statutory Filing.prepare()` creates a deterministic private preparation file and control totals.
- `Malaysia Statutory Filing.reconcile()` verifies unchanged submitted Salary Slip inputs and a zero control difference.
- `malaysia_workforce.diagnostics.get_diagnostics(company)` returns Company, rule-review, payroll setting, employee readiness and filing checks.
- `Malaysia Tax Declaration TP1.relief_catalog(tax_year)` returns the controlled relief-code labels for the reviewed year.

Calculators under `malaysia_workforce.statutory.calculators` are pure deterministic Python functions. Exporters under `malaysia_workforce.statutory.exporters` serialize normalized records; they do not submit to government services.

There is no attendance, availability, roster, employee-profile, work-agreement, bank-transfer, parallel-payroll or custom payroll-release API.
