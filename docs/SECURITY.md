# Security and privacy

Malaysia payroll contains NRIC, tax, contribution, pay and evidence data. Use HTTPS, private files, encrypted backups, tested key rotation and least privilege.

## Role boundaries

- Employee: own TP1/TP3 and ordinary HRMS self-service.
- HR Manager: employee statutory setup, tax review, CP38 and overtime review.
- Payroll processor: standard Payroll Entry/Salary Slip processing.
- Accounts Manager: standard accounting plus statutory-file preparation, submission evidence and reconciliation.
- Auditor: read-only, explicit Company-scoped tax and filing access.
- System Manager: technical administration.

Company User Permissions apply to privileged tax and filing access. An Auditor without an explicit Company User Permission receives no records. Employees are resolved through `Employee.user_id`, not document ownership.

## Controls

- Payroll Entry uses the standard Frappe document lifecycle; the app adds no parallel release state.
- Internal source and file fingerprints protect statutory filing retries and detect changed submitted Salary Slip results. They are hidden from routine forms.
- Salary Slips already included in a submitted statutory filing cannot be casually cancelled.
- Submission evidence and generated files are private Files.
- Version tracking records changes on Malaysia declaration and filing DocTypes.

Frappe role permissions are the first gate; server-side permission-query and document hooks enforce employee/company isolation as a second gate.

## Operational requirements

Separate production identities, require MFA for privileged users, audit role and User Permission changes, restrict backups and database access, test restoration, define retention/correction/breach procedures, and assess DPO duties under Malaysia's current PDPA framework.

Never put real credentials or personal data in test fixtures, repository files, error logs or support screenshots.
