# Security

## Sensitive data

The app stores NRIC/passport, tax, EPF, SOCSO, EIS, payroll and bank-related information. Run only over HTTPS, restrict database/file backups, and apply least-privilege roles.

## Roles

- Employee / Casual Employee: own availability and standard HRMS self-service records.
- Outlet Manager: company/branch-scoped staffing planning and attendance exceptions.
- Malaysia Payroll User: payroll processing.
- Malaysia HR Manager: Malaysian employee and statutory profiles.
- Statutory Administrator: authority files, references, acknowledgements and reconciliation.
- Malaysia Kiosk: desk-disabled integration identity restricted to signed kiosk events.
- Malaysia Workforce Auditor: read-only, explicitly Company-scoped access to staffing, attendance, payroll and statutory evidence.
- System Manager: technical administration.

Employees use the standard Frappe HR portal/PWA plus the authenticated **My Availability** Web Form; they do not need Desk access.

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
- Payroll Entry source/bank hashes and immutable human release identity prevent silent re-release;
- kiosk event IDs are unique and events carry HMAC integrity, device/server timestamps and drift evidence;
- exclusions and ambiguous TP1 claims require HR Manager evidence.

## Recommended controls

- SSO/MFA for HR, payroll and statutory administrators;
- separate payroll processor, attendance approver, HR Manager releaser and auditor roles, plus maker/checker controls in bank and government portals;
- quarterly role review;
- audit-log export and backup testing;
- malware scanning for uploaded evidence/acknowledgements;
- data-retention and secure-destruction policy;
- penetration testing of custom deployment and reverse proxy.

Report security issues privately to the maintainer of your deployed fork; do not include employee data in public issues.

## PDPA operations

The deployer must document lawful purpose, privacy notices, retention periods, employee access/correction handling, processor contracts, encryption/key rotation and secure deletion. Maintain a tested breach runbook using Malaysia's [Data Breach Notification guidance](https://www.pdp.gov.my/ppdpv1/en/akta/personal-data-protection-guidelines-on-data-breach-notification-dbn/): assess significant harm promptly, notify the Commissioner within the prescribed 72 hours when required, retain confirmation, and complete phased information within the applicable period. Assess and document whether a DPO is required, and keep evidence of backup encryption and periodic restore tests. These are employer operating procedures, not background actions the app may silently perform.

## Employee-facing rendering

Use Frappe controls and message APIs for employee-facing errors; do not inject server text into unescaped HTML.
