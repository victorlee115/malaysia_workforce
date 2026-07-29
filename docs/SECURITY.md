# Security

## Sensitive data

The app stores NRIC/passport, tax, EPF, SOCSO, EIS, payroll and bank-related information. Run only over HTTPS, restrict database/file backups, and apply least-privilege roles.

## Roles

- Casual Employee: own employee portal records.
- Roster Manager: roster planning and approved operational scope.
- Malaysia Payroll User: payroll processing.
- Malaysia HR Manager: Malaysian employee and statutory profiles.
- Statutory Administrator: authority files, references, acknowledgements and reconciliation.
- System Manager: technical administration.

Employees must not receive Desk access merely to use `/workforce`.

## Files

Authority files are created as private Frappe File records and stored with SHA-256 checksums. Do not email unencrypted statutory files unless your security policy explicitly permits it.

## Portal credentials

The app does not store MyTax, i-Akaun or ASSIST passwords and does not automate OTPs. Use the official portal in a separate authenticated session.

## Audit protections

- treatment history is immutable;
- submitted Salary Slip snapshots are locked;
- accepted/submitted statutory source lines and files are locked;
- corrections use revisions;
- payroll source hashes prevent work-record drift;
- generated Additional Salary rows use idempotency keys.

## Recommended controls

- SSO/MFA for HR, payroll and statutory administrators;
- separate maker/checker controls in the bank and government portals even though statutory profile changes do not require app approval;
- quarterly role review;
- audit-log export and backup testing;
- malware scanning for uploaded evidence/acknowledgements;
- data-retention and secure-destruction policy;
- penetration testing of custom deployment and reverse proxy.

Report security issues privately to the maintainer of your deployed fork; do not include employee data in public issues.

## Portal rendering

Server-provided error text is escaped before insertion into HTML-capable dialogs. Keep this invariant for all new employee-facing API errors.
