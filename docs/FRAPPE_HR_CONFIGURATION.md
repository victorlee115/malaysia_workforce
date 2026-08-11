# Standard Frappe HR ownership

Malaysia Workforce is a localisation layer. Configure these operations in standard Frappe HR/ERPNext and do not build parallel DocTypes:

- Applicant, Job Opening, Interview, Job Offer, Appointment Letter, Employee Onboarding, Employee, transfer, promotion, appraisal, training, separation and exit interview;
- Employment Type, Department, Branch, Designation, Holiday List, Shift Type, Shift Assignment, Employee Checkin, Attendance and Attendance Request;
- Leave Type, Leave Policy, Leave Policy Assignment, Leave Application, Employee Advance and Expense Claim;
- Salary Component, Salary Structure, Salary Structure Assignment, Additional Salary, Payroll Entry, Salary Slip and payroll accounting;
- Workflow, Assignment/ToDo, Notification, User Permission, Role Permission, File, Comment, Version and Audit Trail.

## Required configuration

1. Create the correct Holiday List for each outlet/state and assign it through standard Company/Employee/Shift settings.
2. Configure standard leave types and effective policies for annual, sick, hospitalisation, maternity, paternity and public-holiday substitution. Maintain separate policies where full-time and part-time entitlements differ; do not put one universal entitlement in code.
3. Enable HR Settings → Allow Multiple Shift Assignments for Same Date only if the cafe genuinely permits split shifts.
4. Configure Shift Type auto-attendance from `Employee Checkin`; the kiosk must not create `Attendance` directly.
5. Missed-punch requests create pending standard `Employee Checkin` pairs. A different manager approves or rejects them with evidence; if standard Attendance already exists, the app assigns a reprocessing task rather than silently replacing Attendance. Standard Attendance Request remains available for ordinary HRMS attendance-status corrections.
6. Use standard self-service for published shifts, Shift Requests, leave, claims, attendance history, payslips, onboarding and employee details. The only additional employee surface is the native **My Availability** Web Form; check-ins use the registered cafe kiosk.
7. Create an authenticated standard Web Form/Workflow on Employee for the Malaysia privacy acknowledgement Attach field. Keep the notice itself as a private standard File linked from Company; do not build a separate consent portal.
8. Configure Company and Employee User Permissions and role permissions for manager, attendance approver, payroll processor, HR Manager releaser and auditor. Do not grant the kiosk user Desk access or broad Employee reads.
9. Use standard training records and attach/link HRD Corp levy or grant evidence; use standard Issue plus assigned ToDo for workplace incidents.
10. Keep full-time/monthly payroll in standard Frappe HR. RC7's derived flexible-work pay calculation accepts reviewed hourly part-time/casual agreements only; non-hourly flexible-worker cases fail closed until a separate Malaysian rule review and UAT exist.

## Malaysia-specific records that remain

- `Malaysia Employee Profile`: restricted identity/statutory/tax data only.
- `Employee Work Agreement`: effective-dated Malaysian legal-terms addendum only; it is not onboarding or employment status.
- `Shift Work Record`: derived immutable pay-band snapshot/reservation only; it is not attendance.
- statutory coverage, treatment history, accumulators, submissions, annual preparation records and employee notifications, because HRMS has no Malaysian equivalents.

No Frappe/ERPNext/HRMS core file is patched. Integrations use hooks, custom fields, standard records and explicit adapter boundaries.
