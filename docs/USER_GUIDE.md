# Malaysia Payroll for Frappe HR: beginner's guide

This guide takes a cafe operator from an empty Frappe HR setup to a completed monthly payroll and statutory handoff. You do not need a separate HR system or a custom employee portal.

It is written for a person who has never run HR or payroll. Follow the sections in order for the first setup. After setup, use the role instructions and monthly checklists as your operating procedure.

## How to use this guide

- **Setting up for the first time:** read sections 1–7 in order.
- **Employee:** use sections 3 and 8.
- **HR Manager:** use sections 7–10 and the daily routine.
- **Payroll processor:** use sections 6, 7.6 and 11.
- **Accounts Manager:** use sections 11.5 and 12.
- **Auditor:** use sections 2, 11.4, 12A, 13 and 15.
- **When something goes wrong:** use sections 13 and 16.

Keep the monthly checklist in section 14 open while payroll is running. Do not rely on memory.

The operating rule is:

> Use Frappe HR for normal HR and payroll. Use this localisation only for Malaysian statutory details, calculations, declarations and authority preparation.

The app does not replace Employee, Contract, Salary Structure, Payroll Entry, Salary Slip, attendance, leave, expenses, shifts, accounting or the HRMS mobile app.

## Start here: the system in plain language

The whole system has five layers:

1. **Employee facts** — who the person is, where they work and their Malaysian statutory identifiers.
2. **Employment terms** — their wage basis, normal hours, rest day and recurring pay.
3. **Monthly changes** — attendance, leave, overtime, one-off pay, TP1, TP3, CP38 and zakat.
4. **Payroll result** — Payroll Entry gathers employees; Salary Slip calculates each employee's gross pay, deductions and net pay.
5. **Government handoff** — Statutory Filing prepares an authority file from submitted Salary Slips. A human validates, uploads, pays and records the receipt.

```text
Set up Company and payroll rules once
    → add and maintain Employees
    → record the month's attendance, leave and pay changes
    → run Payroll Readiness
    → create Payroll Entry and Salary Slips
    → review, submit, account and pay
    → prepare EPF, PERKESO, LHDN and HRD Corp handoffs
    → attach authority evidence and reconcile
```

If a result is wrong, correct the earlier source record. Do not type a balancing number into the final Salary Slip just to make it look right.

### Five Frappe words you must understand

| Word | Plain meaning |
|---|---|
| **DocType** | A type of record, such as Employee, Contract or Salary Slip. |
| **List** | The page showing many records of one type. Use filters to find a person, period or status. |
| **Form** | One record. Open it to view or edit its fields and attachments. |
| **Save** | Store a working draft. A saved draft can normally still be edited. |
| **Submit** | Finalise an operational record. Submitted records should not be edited directly; cancel and amend them through Frappe when correction is legally and operationally appropriate. |

Other useful controls:

- Use the top search bar to type the exact screen name, for example `Employee`, `Payroll Entry` or `Malaysia Payroll Readiness`.
- An orange dot or **Not Saved** means the form has changes. Select **Save** before leaving.
- The **Connections**, **Dashboard** or linked-document area shows records related to the current form.
- The timeline at the bottom records comments, changes and workflow events.
- **Menu → Reload** refreshes a record. Do not repeatedly click Submit while the page is working.
- Attachments containing identity, tax or payroll data must be marked private and shared only with authorised users.

### Draft, Submitted, Cancelled and Amended

| Status | What it means | What the user should do |
|---|---|---|
| Draft (`0`) | Still being prepared | Correct it, review it and then submit when ready. |
| Submitted (`1`) | Final and relied upon | Do not edit around it. Use the normal cancellation/amendment path if a correction is required. |
| Cancelled (`2`) | Reversed and retained in history | Create an amended record when replacement is needed. |
| Amended | A new record linked to a cancelled original | Review and submit the new record; never delete the history. |

### Malaysian payroll words in this guide

| Term | Plain meaning in this system |
|---|---|
| EPF / KWSP | Retirement contribution with employee and employer amounts. |
| PERKESO / SOCSO | Social-security contribution with employee and employer amounts. |
| EIS | Employment Insurance System contribution with employee and employer amounts. |
| LINDUNG 24 Jam / SKBBK | The additional PERKESO employee amount carried with the current combined PERKESO result/file. |
| PCB / MTD | Monthly income-tax deduction calculated from current and year-to-date supported inputs. |
| TP1 | Employee declaration of eligible optional reliefs for PCB consideration. It needs evidence and HR review. |
| TP3 | Previous-employment amounts in the same tax year used for cumulative PCB. Do not estimate them. |
| CP38 | An additional tax deduction required by a specific LHDN directive. It is separate from ordinary PCB. |
| Zakat | An employee deduction maintained in normal payroll and used as a supported PCB rebate input. |
| HRD Corp levy | Employer-only levy calculated from the configured registration class and leviable wages. |
| Wage base | The earnings included for one scheme. EPF, SOCSO, EIS, HRD and PCB bases can differ. |
| Employee amount | Money deducted from the employee's pay. |
| Employer amount | Extra Company cost; it does not reduce the employee's net pay. |

These are operational explanations, not legal definitions. Use the official source and qualified review for unusual cases.

### What “automation” does and does not mean

The app calculates reviewed rules and prepares files. It does not decide whether an employee has made a truthful declaration, whether an unusual payment is legally classified correctly, whether a government portal accepted a file, or whether money left the bank. Keep one accountable human for approvals and periodic professional review.

## 0. Beginner quick start: one complete, safe payroll

If you have never used HR software, follow this order. Do not jump straight to payroll: each step creates information that the next step needs.

| Step | Who does it | Where to go | What to do | What success looks like |
| --- | --- | --- | --- | --- |
| 1 | System Manager | **Company** | Create the company, currency, country and accounting settings | The company can be selected on an Employee and Payroll Entry |
| 2 | System Manager / HR Manager | **Employee** | Create the employee, User login, job details and Malaysian statutory details | The employee is active and has no red setup warnings |
| 3 | HR Manager | **Contract**, **Salary Structure**, **Salary Structure Assignment** | Record the employee's terms and recurring pay | The assignment has a start date and all required components |
| 4 | Employee | HRMS home / mobile browser | Sign in, check personal details and submit availability or leave when required | The manager can see the request in Desk |
| 5 | Manager / attendance approver | **Shift Assignment**, **Employee Checkin**, **Attendance** | Publish shifts and approve attendance corrections | Attendance is submitted for the pay period |
| 6 | Payroll Processor | **Malaysia Payroll Readiness**, then **Payroll Entry** | Resolve every red readiness item, calculate Salary Slips and review totals | Every employee has one Salary Slip with the expected net pay |
| 7 | HR Manager / authorised releaser | **Payroll Entry** | Approve and release payroll after the maker's review | Release evidence is recorded and payroll is not silently changed afterwards |
| 8 | Accounts / payroll processor | **Malaysia Statutory Filing** | Prepare authority files, reconcile totals and attach upload evidence | Each file has a known status and a responsible person |
| 9 | Employee | HRMS home / **Salary Slip** | Download the payslip | The employee sees gross pay, deductions, statutory amounts and net pay |

For practice, do this on a staging site with one test employee and a small test amount. Never upload a staging file to a live bank or government portal.

### 0.1 The three screens you will use most

1. **Desk** is the back office. Use the search box at the top to find a DocType such as `Employee`, `Payroll Entry`, `Salary Slip` or `Malaysia Statutory Filing`.
2. **HRMS home / PWA** is the employee view. Employees use it for their profile, leave, attendance, claims and payslips; they should not need Desk.
3. **The list view** shows many records. Click a record to open it, make a change, and use **Save**. A submitted document is normally locked; use the documented correction process instead of editing the database.

### 0.2 First login: check these things before real data

1. Open the site and sign in with the account created for your role.
2. Look at the top-right user menu and confirm the correct user name.
3. Use the search box to open **Company**. If there is no company, stop and ask the System Manager to complete setup.
4. Check that the site uses `Asia/Kuala_Lumpur` time and the correct currency.
5. Open **Employee** and confirm that you can see only the employees your role is allowed to see. If you can see another company's employees, stop and report it.
6. Keep the **Payroll Processor**, **HR Manager**, **Accounts** and **Employee** accounts separate. Never test employee self-service while logged in as an administrator.

### 0.3 Create one practice employee

Use a realistic test identity, not a real employee's NRIC or bank account.

1. Open **Employee** and select **New**.
2. Enter the employee name, date of joining, company, department, branch, designation and employment type.
3. Save the Employee. Create or link the User account only after the Employee record exists.
4. Open the Malaysian/statutory section and complete the required EPF, SOCSO/PERKESO, EIS, PCB and tax identifiers. Do not leave a field blank merely to make a warning disappear.
5. If the employee is subject to LINDUNG or another optional scheme, select it only when eligibility evidence is available.
6. Save and run **Malaysia Payroll Readiness** for the employee. A red item means “stop”; it is not an informational suggestion.

### 0.4 Give the employee a pay arrangement

1. Open **Contract** and create the employee's approved terms. Use the effective date on which the terms actually start.
2. Open **Salary Structure** and select the approved earning and deduction components. Use each component's Malaysian statutory treatment; never guess treatment from its name.
3. Open **Salary Structure Assignment**, select the employee, company, salary structure, base amount and start date, then save and submit it.
4. Use **Additional Salary** for a one-off approved item such as a bonus or allowance. Do not edit a submitted Salary Slip to add it.
5. Re-run **Malaysia Payroll Readiness**. Continue only when the employee is eligible and component classification is complete.

### 0.5 Run the first practice payroll

1. Confirm attendance, approved leave and any approved overtime for the period.
2. Open **Malaysia Payroll Readiness** for the company and pay period. Fix every red item; record an exception for anything that genuinely needs a human decision.
3. Open **Payroll Entry** and select the company, payroll frequency, start date and end date.
4. Use **Get Employees**. Check the employee list and investigate why an expected employee is missing; do not create a duplicate employee.
5. Use the readiness/validation action supplied on the form. Do not continue if the period, statutory profile, salary structure or account mapping is incomplete.
6. Create the Salary Slips. Open each **Salary Slip** and check the employee, period, payment days, earnings, deductions, employer contributions and net pay.
7. Compare Payroll Entry totals with the expected practice amounts. A difference is a reason to stop, not a rounding detail to ignore.
8. Have a second authorised person review the entry. The person who prepared it must not be the final releaser.
9. Submit and release only after the review is complete. Record the release evidence required by your company procedure.
10. Open **Malaysia Statutory Filing**, select the period and authority, prepare the file, and compare its totals with the Salary Slips. Keep the generated file and upload/acceptance evidence together.
11. Do not claim that a government or bank submission succeeded until the authorised person has uploaded it and recorded the receipt or confirmation number.

### 0.6 The employee's first self-service visit

Give the employee the site address and their own login. Tell them to:

1. Open HRMS home on a phone or computer and sign in.
2. Open **My Profile** and check their name, email, phone, bank details and emergency contact. Ask HR to correct anything wrong; do not create a second Employee record.
3. Open **Leave** to see balances and submit a Leave Application when needed.
4. Open **Attendance** to review check-ins and use the supplied correction request if a punch is missing.
5. Open **Salary Slips** after payroll is released and download the payslip.
6. Use the Malaysia tax forms only when HR has asked for them. Upload evidence with the request; never email an NRIC or tax document to an unverified address.

### 0.7 Stop signs for beginners

- **Red validation message:** stop and fix the named record.
- **Missing employee:** check company, employment dates, salary assignment and payroll filters; do not create a duplicate employee.
- **Unexpected net pay:** open the Salary Slip and compare payment days, attendance, components and statutory deductions; ask the Payroll Processor before releasing.
- **A button is missing:** your role probably does not have that permission. Do not use another person's login.
- **A document is submitted:** do not edit it directly. Use the correction, amendment or reversal process described later in this guide.
- **A file is “prepared” but not “submitted”:** it is still your team's responsibility to upload it and record the official confirmation.

## Your first implementation week

Do not begin with a live payroll. Use this order:

1. System Manager completes the technical installation and creates named user accounts.
2. System Manager configures Company, Fiscal Year, Holiday List, Payroll Period, accounts and Payroll Settings.
3. HR Manager configures Salary Components and Overtime Types with a Malaysian payroll specialist.
4. HR Manager adds one test Employee, Contract and Salary Structure Assignment.
5. The employee signs in to HRMS and verifies their own profile and self-service access.
6. Payroll processor runs Payroll Readiness and a draft test payroll.
7. HR Manager checks the Salary Slip line by line against an independent calculation.
8. Accounts Manager prepares test authority files and validates them in the current official portal or validator without making a real payment.
9. Repeat with every employee category that will be used.
10. Run at least two parallel months before go-live.

Do not enable a category just because one sample employee worked. Test full-month, joiner, leaver, unpaid leave, overtime, bonus and correction cases relevant to your company.

## 1. Before using real payroll data

The current release is a staging/UAT candidate. Do not use its output for live payment or submission until all production gates pass:

- install and migrate twice on a clean, officially compatible pinned stack;
- run at least two parallel payroll months and an off-cycle or year-boundary case;
- obtain zero unexplained employee or authority-total differences;
- validate EPF, PERKESO and LHDN files in their current official portal or validator;
- test private-file access, permissions, backups and a full restoration;
- obtain sign-off from the accountable employer and a Malaysian payroll specialist.

An attached file means “prepared by Frappe,” not “accepted by the authority.” A human still reviews, uploads, authorises payment and stores the real receipt.

Phase 1 supports Peninsular Malaysia and Malaysian citizens or permanent residents under ordinary resident PCB treatment. Unsupported cases stop instead of being estimated.

## 2. Who uses each part

Use separate named accounts. Never share one payroll login.

| Person | Uses | Main responsibility |
|---|---|---|
| Employee | Standard HRMS mobile/PWA; TP1 and TP3 Web Forms | Own attendance, leave, claims, payslips and tax declarations |
| HR Manager | Standard Employee and Contract forms; TP1/TP3 workflow; CP38 | Maintain statutory details and review evidence |
| Payroll processor | Standard Payroll Entry and Salary Slip | Prepare payroll, run readiness, review results |
| Accounts Manager | Standard accounting; Statutory Filing | Prepare authority files, record evidence and reconcile |
| Auditor | Read-only records and reports | Verify history, totals and evidence |
| System Manager | Company setup, permissions, upgrades and backups | Technical administration, not routine payroll processing |

Company User Permissions should restrict privileged users to the companies they actually manage. An employee is restricted to the Employee linked to their own User ID.

### Simple separation of duties

For a small cafe, one person may hold more than one role, but use different approval steps and never approve your own input. At minimum:

- the employee or supervisor records attendance and claims;
- HR Manager checks employee facts, evidence and unusual changes;
- payroll processor prepares Payroll Entry and draft Salary Slips;
- an authorised reviewer compares totals and approves the real payment;
- Accounts Manager prepares and submits authority files;
- Auditor can inspect but cannot change records.

The person who entered a correction should not be the only person checking it. This matters most for bank details, pay rates, attendance corrections, one-off deductions and authority totals.

### What each user must never do

| User | Never do this |
|---|---|
| Employee | Share a password, claim another employee's relief, or estimate TP3 figures. |
| HR Manager | Change submitted payroll history directly or accept unsupported evidence. |
| Payroll processor | Add manual statutory deductions to force a desired net pay. |
| Accounts Manager | Mark a filing Accepted without the real acknowledgement. |
| Auditor | Use a privileged account to “help” edit a record being audited. |
| System Manager | Use Administrator for routine HR or payroll work. |

## 3. Where to work

Managers use normal Frappe Desk. The **Malaysia Payroll** Workspace is the one country-level entry point for:

- TP1 tax reliefs;
- TP3 previous-employment amounts;
- CP38 directives;
- Payroll Readiness;
- standard Payroll Entries and Salary Slips;
- Statutory Filings;
- Annual Remuneration.

Employees use the standard Frappe HR app at:

```text
/login?redirect-to=/hrms/home
```

Send employees directly to these forms when needed:

```text
/my-tax-reliefs/new
/my-previous-employment/new
```

There is no separate Malaysia employee portal. On phones, employees can install the normal Frappe HR PWA from their browser.

### Recommended bookmarks

Give each user only the links they need:

| User | Bookmark |
|---|---|
| Employee | `/login?redirect-to=/hrms/home` |
| Employee submitting TP1 | `/my-tax-reliefs/new` |
| Employee submitting TP3 | `/my-previous-employment/new` |
| Manager or payroll user | `/app/malaysia-payroll` |

Replace the domain with your real HTTPS site. Do not train employees to use the wide Desk interface on a phone; the standard HRMS PWA is the employee mobile experience.

### If you cannot find a screen

1. Return to Desk.
2. Use the top search bar.
3. Type the exact bold screen name from this guide.
4. If it does not appear, ask System Manager to check your role and Company User Permission. Do not ask for System Manager access as a shortcut.

## 4. One-time technical setup

The System Manager or implementation partner should:

1. Install the exact Frappe, ERPNext, HRMS, Python, Node and MariaDB versions in `compatibility-lock.json`.
2. Install ERPNext and HRMS before this app.
3. Run `bench --site <site> migrate` twice.
4. Build assets and run the Python, JavaScript, release and live-workflow checks.
5. Run the full Bench process set: web, Redis, Socket.IO, workers and scheduler.
6. Configure HTTPS, MFA for privileged accounts, encrypted backups and private-file retention.

Do not patch Frappe, ERPNext or HRMS core files.

## 5. Configure the organisation

### 5.1 Global records

Create or confirm these standard records:

- System time zone: **Asia/Kuala_Lumpur**;
- default country: **Malaysia**;
- default currency: **MYR**;
- a Fiscal Year covering the payroll date;
- a Holiday List with the correct public and weekly holidays;
- a Payroll Period covering the year.

In **Payroll Settings**, enable **Include holidays in Total no. of Working Days**. Payroll submission is blocked if this is off because incomplete-month monthly pay uses calendar days.

Create the records in this order:

1. Open **System Settings** and set Time Zone to `Asia/Kuala_Lumpur`.
2. Open **Global Defaults** and set Country to `Malaysia` and Currency to `MYR`.
3. Create a **Fiscal Year** with the correct start and end dates. Save it and ensure it applies to the Company.
4. Create a **Holiday List**. Add every applicable public holiday and the employee's weekly holiday pattern. Do not copy another state blindly because Malaysian public holidays differ by location.
5. Create a **Payroll Period** covering the calendar or tax year used by your pay cycle. This is also needed for employees to see Salary Slips in HRMS.
6. Open **Payroll Settings**, enable **Include holidays in Total no. of Working Days**, then save.

Before proceeding, search for each record and reopen it. This catches records that were typed but never saved.

### 5.2 Company

Open the standard Company and its **Statutory Payroll** tab.

1. Confirm Country = Malaysia and default currency = MYR.
2. Enable **Statutory Payroll**.
3. Keep Payroll Jurisdiction = Peninsular Malaysia for phase 1.
4. Enter the SSM registration number.
5. Enter the LHDN HQ and employer numbers. Use the standard Company Tax ID field for the employer TIN.
6. Enter the EPF employer number and PERKESO employer code.
7. Select the real HRD Corp registration class.
8. When registered, enter its registration number and effective date.

Company setup belongs to System Manager. They can open **Malaysia Payroll Readiness** and **Malaysia Annual Remuneration** for implementation checks; day-to-day use stays with HR Manager, Accounts Manager and Auditor. HR Manager does not need broad Company or Sales Invoice permission merely to run payroll.

#### How to choose HRD Corp Registration

- Choose **Compulsory (1%)** when the company is compulsorily registered.
- Choose **Optional (0.5%)** only when the company actually completed optional registration.
- Choose **Not Registered** only when that matches the company's real position.

The system counts active Malaysian employees on the payroll date and blocks an obvious conflict, such as ten or more employees with the Company marked Not Registered. It cannot complete the registration for you. Store the official registration record securely outside or as a private Frappe attachment according to your document policy.

#### Company setup check

Do not continue until the Company form shows all of the following:

- Country `Malaysia`;
- Currency `MYR`;
- Statutory Payroll enabled;
- Peninsular Malaysia jurisdiction;
- SSM, LHDN, EPF and PERKESO identifiers;
- truthful HRD Corp status, number and effective date where applicable.

### 5.3 Accounting

Using normal ERPNext setup, configure:

- payroll payable account;
- salary and overtime expense accounts;
- cost centres;
- bank and payment accounts;
- Company accounts on every Salary Component used in payroll.

This localisation calculates payroll but does not transmit salary money.

Ask the person responsible for ERPNext accounting to perform a small test posting. A correct Salary Slip with missing Salary Component accounts can still fail later when Payroll Entry creates accounting entries.

Use a controlled bank-payment process:

1. Payroll processor produces the approved payroll total.
2. A separate authorised person compares employee bank details and the bank total.
3. The authorised person prepares or uploads the bank instruction using the company's approved bank process.
4. A second bank approver authorises payment where the bank supports maker/checker.
5. Store the bank reference and reconciliation evidence according to company policy.

This app does not generate or upload a bank bulk-payment file in phase 1.

## 6. Configure pay components

For every earning Salary Component, open **Statutory Treatment** and record whether it is included in:

- EPF wages;
- SOCSO wages;
- EIS wages;
- HRD levy wages;
- PCB as regular, additional or non-taxable remuneration;
- ordinary rate of pay.

Do not guess. Have a Malaysian payroll reviewer approve the treatment matrix for basic pay, allowances, bonus, commission and overtime.

### Configure each earning step by step

1. Search for **Salary Component**.
2. Open one earning component, for example Basic Pay or a real allowance used by the Company.
3. Confirm Type is **Earning**.
4. Open the collapsed **Statutory Treatment** section.
5. For each scheme, decide whether this component forms part of the wage base.
6. Select exactly one **PCB Treatment**:
   - **Regular Remuneration** for remuneration paid in the ordinary recurring cycle;
   - **Additional Remuneration** for a qualifying additional payment;
   - **Not Taxable** only when an approved rule says the payment is outside PCB remuneration.
7. Select **Include in Ordinary Rate of Pay** only when the approved pay policy and law require it for rate calculations.
8. Save.
9. Repeat for every earning that can appear in a Salary Structure or Additional Salary.

A blank PCB Treatment is not a harmless blank. Payroll deliberately stops because an unclassified earning could under-deduct tax or other contributions.

Keep an approved worksheet with one row per Salary Component and these columns:

| Salary Component | EPF | SOCSO | EIS | HRD | PCB treatment | Ordinary rate | Reviewed by/date |
|---|---:|---:|---:|---:|---|---:|---|
| Use your real component | Yes/No | Yes/No | Yes/No | Yes/No | One selection | Yes/No | Named reviewer |

Do not copy a generic Internet example into production. Treatment can depend on what the payment actually represents, not merely its label.

The app owns these deduction components:

- EPF Employee;
- SOCSO Employee;
- SKBBK Employee, which carries the LINDUNG 24 Jam amount in the current combined PERKESO specification;
- EIS Employee;
- PCB;
- CP38;
- Zakat.

Configure accounts on them. Do not add hand-calculated EPF, SOCSO, LINDUNG, EIS, PCB or CP38 rows to Salary Structures; draft Salary Slips receive the calculated deductions automatically.

Zakat remains a normal recurring or Additional Salary deduction. The calculator uses the same amount as the PCB rebate.

### Configure overtime masters once

Create normal HRMS **Overtime Type** records for the cases the cafe uses. For each type:

1. Select the real overtime Salary Component.
2. Complete the standard HRMS calculation settings.
3. Select the added **Statutory Day Type** as Normal Overtime, Rest Day or Public Holiday.
4. Save and test the type with a submitted Attendance record and a draft Overtime Slip.

Do not use one generic overtime type for all three day types. Their legal calculations differ.

## 7. Add an employee

Treat onboarding as a sequence. A person is not payroll-ready merely because an Employee record exists.

```text
User login
    → Employee
    → statutory details
    → active Contract
    → submitted Salary Structure
    → submitted Salary Structure Assignment
    → Holiday List and Payroll Period coverage
    → Payroll Readiness = Ready
```

### 7.1 Use the standard lifecycle

When needed, use standard Applicant, Interview, Job Offer, Appointment Letter and Employee Onboarding. Then create the normal Employee record.

### 7.2 Create the employee login

1. Create a User with the employee's own email address.
2. Create the Employee and link that User under **User ID**.
3. Set the User Type to **Employee Self Service**.
4. Do not give the employee HR, Accounts or System Manager roles.
5. Send the employee through the normal password setup process.

Ask the employee to sign in immediately. If they cannot open HRMS during onboarding, they will not be able to request leave, view Salary Slips or submit their own tax information later.

### 7.3 Complete Employee

On the standard Employee form, enter the normal name, Company, date of birth, joining date, status, department, branch, designation, Holiday List, User ID and bank details.

Use the name and identity exactly as supported by the employee's official documents. A spelling or identifier change after a filing is prepared invalidates the prepared file and requires it to be prepared again.

Open **Statutory Details** and enter:

- Citizenship Status;
- NRIC;
- SOCSO Category;
- EIS eligibility;

For the `Standard Payroll` profile, also enter:

- Tax Identification Number;
- EPF Member Number;
- PCB resident status, category, child units and disability flags.

#### Contractor profile: SOCSO + EIS — LINDUNG Optional

If you want to manage a contractor in the same Employee, Contract and Salary Slip screens but only calculate SOCSO, EIS and optional LINDUNG:

1. Leave the person as a normal Frappe **Employee** and set **Employment Type** to `Contractor` if that label is useful to you. Employment Type does not control statutory calculations.
2. Set **Statutory Profile** to `SOCSO + EIS — LINDUNG Optional`. Do not rely on Employment Type alone.
3. Complete **NRIC**, **SOCSO Category** and **EIS Eligible**. EIS must be enabled for this profile.
4. Leave the TIN, EPF member number, PCB category, TP1, TP3 and CP38 information blank. Those tax fields are hidden for this profile and the tax forms are unavailable.
5. Keep or change **LINDUNG 24 Jam Participation** using the same evidence rules below. `Participating` includes the SKBBK/LINDUNG amount; `Not Participating` requires the employee's own valid release notice.
6. Create the normal active **Contract**, **Salary Structure** and **Salary Structure Assignment**. At least one earning component must be included in both SOCSO and EIS wages.
7. Run **Malaysia Payroll Readiness**. The report shows the profile so you can tell which missing fields are expected. A contractor can be in the same Payroll Entry as standard employees.

The resulting Salary Slip contains gross pay, SOCSO, EIS and LINDUNG when applicable. It does not calculate EPF, PCB, CP38, Zakat or HRD Corp for this profile. The contractor is included in the combined PERKESO handoff and excluded from EPF, LHDN and HRD Corp handoffs. Malaysia Annual Remuneration hides this profile unless you tick **Show All Statutory Profiles**.

LINDUNG 24 Jam has applied since 1 June 2026 and stays on by default. Leave **Participation** on `Participating` unless the employee has personally filed a Liability Release Notice (*Notis/Perakuan Pelepasan Liabiliti*) on the LINDUNG Faedah portal. The employer may not file it on the employee's behalf, but must stop deducting once notified. Only then set:

- Participation to `Not Participating`;
- the employee's PERKESO registration date;
- the effective date shown on the notice;
- the notice itself as the attachment.

If the employee has more than one employer, tick **Has Multiple Employers**. Phase 1 stops that employee's payroll because PERKESO permits only its selected employer to deduct LINDUNG; do not clear the flag merely to make payroll pass.

Never record `Not Participating` without the employee's own Liability Release Notice. An employee who files nothing is treated as participating (PERKESO FAQ Q20), so recording an unsupported release under-deducts, leaves the employer liable, and removes the employee's cover — an accident is not payable for someone recorded as having opted out (Q40).

Timing follows the payroll run, not the calendar. Record the release before you submit that month's Salary Slips and the deduction stops for that month; record it after, and the submitted slip stands and the next month stops. June 2026 contributions are mandatory and never refundable (Q8), and if June was missed for a participant the employer owes the arrears (Q18).

Two limits to know:

- **The declaration window is closed and one-way.** Existing employees could decline only between 13 July and 31 August 2026 (Q16). A participant is *"sekali layak terus layak"* — once eligible, always eligible — and cannot stop contributing later (Q6).
- **A new hire has 30 days.** A newly registered local employee has 30 days from registration to decline (Q22), so the August 2026 cutoff does not apply to them.

#### Before saving Employee

Check all of these:

- the User ID belongs to this employee and no one else;
- Company, date of birth, joining date and Holiday List are correct;
- citizenship and NRIC match evidence;
- for `Standard Payroll`, TIN, EPF member number and PCB residence/category, spouse and child information match the supported declaration;
- for `SOCSO + EIS — LINDUNG Optional`, EIS is enabled and the SOCSO/EIS wage components are classified;
- SOCSO category and EIS eligibility were reviewed, not assumed;
- bank information follows your separate verification procedure;
- any LINDUNG exception has the employee's own notice and valid dates.

### 7.4 Create the standard Contract

Create a normal ERPNext Contract with Party Type = Employee. Open **Statutory Working Terms** and enter:

- Monthly, Daily or Hourly wage basis;
- Full-time or Part-time classification;
- normal hours per day and week;
- rest day;
- overtime eligibility;
- daily or hourly rate when that is the wage basis;
- comparable full-time daily and weekly hours for a part-time employee.

Salary Structure Assignment is authoritative for a monthly base. Contract provides effective legal and calculation context; it is not a second salary record.

Create it as follows:

1. Search for **Contract** and select **Add Contract**.
2. Set Party Type to **Employee** and Party Name to the employee.
3. Enter Start Date and, only when known, End Date.
4. Ensure the Contract is **Active** for the period in which payroll will run.
5. Complete the normal contract terms or template used by the Company.
6. Open **Statutory Working Terms** and enter the fields listed above.
7. Save and submit or otherwise activate it according to the standard ERPNext Contract lifecycle used by the Company.

For monthly employees, do not type the monthly salary into Daily or Hourly Rate. Their monetary base comes from the submitted Salary Structure Assignment. For daily and hourly employees, the added rate is required.

The system rejects normal hours above eight per day or 45 per week. A part-time employee also needs the comparable full-time hours because part-time additional work, rest-day and public-holiday rules use that comparison.

### 7.5 Assign salary

1. Create and submit a standard Salary Structure.
2. Add recurring earnings and ordinary recurring deductions.
3. Create and submit a Salary Structure Assignment with the effective From Date and base amount.
4. Use Additional Salary for approved one-off earnings or deductions.

Before first payroll, run **Payroll Readiness** and fix every named issue.

#### Salary Structure setup in plain language

- **Salary Component** says what a line means, such as Basic Pay or Meal Allowance.
- **Salary Structure** is a reusable collection of earnings and recurring deductions.
- **Salary Structure Assignment** attaches that structure and its base to one employee from a date.
- **Additional Salary** is a one-off or variable amount for a particular payroll date.

Use this sequence:

1. Open or create a Salary Structure for the relevant employee group.
2. Add only approved recurring components and formulas.
3. Confirm every earning component has Statutory Treatment and every component has the correct Company account.
4. Submit the Salary Structure.
5. Create a Salary Structure Assignment for the employee.
6. Set the correct effective From Date, income-tax slab and base amount where applicable.
7. Submit the assignment.
8. Use Additional Salary later for approved bonuses, commissions or deductions that are not recurring.

Never overwrite an old effective assignment to represent a pay rise. Create the new effective record through the standard HRMS process so past payroll remains explainable.

### 7.6 New-employee readiness check

Open **Malaysia Payroll Readiness**, select the Company and a date inside the employee's first payroll, then enable **Show Ready Employees**. The employee is ready only when the row is green and says Ready.

Common failures and their owners:

| Readiness message | Record to open | Usually fixed by |
|---|---|---|
| Date of Birth, NRIC, TIN or member number missing | Employee → Statutory Details | HR Manager |
| No Salary Structure Assignment | Salary Structure Assignment | Payroll processor/HR Manager |
| Set PCB Treatment for earning components | Named Salary Component | HR Manager with payroll reviewer |
| No active Contract | Contract | HR Manager |
| Contract working terms incomplete | Contract → Statutory Working Terms | HR Manager |
| No Holiday List | Employee or Company Holiday List setup | HR Manager |
| No active Fiscal Year | Fiscal Year | System Manager/Accounts |

## 8. Employee self-service

After signing in to `/hrms/home`, the employee uses normal Frappe HR for:

- check-in and attendance requests;
- shift requests;
- leave applications;
- expense claims and advances;
- payslips;
- profile information.

If Salary shows no payslips, HR should verify that the User is linked to the correct Active Employee, the Salary Slip is submitted and a standard Payroll Period covers its date.

### First employee sign-in

1. Open the HRMS link supplied by the Company.
2. Sign in with your own email and password.
3. Open **Profile** and check that the name and employee details are yours.
4. Open **View Salary Slips** from HRMS home. Use that tile rather than typing `/hrms/home/salary`, which can render a blank Frappe HR page. It is normal to see no Salary Slips before the first completed payroll.
5. Open **Leaves**, **Attendance** and **Expenses** so you know where future requests are made.
6. Sign out, then sign in again to confirm the password works.

If another person's information appears, stop immediately, sign out and report it. Do not continue browsing their information.

### Ordinary employee tasks

| Need | Use in standard HRMS | What happens next |
|---|---|---|
| Request leave | Leave Application | The configured leave approver reviews it. |
| Correct attendance | Attendance Request | The attendance approver reviews it; explain what is missing or wrong. |
| Request a shift change | Shift Request | The manager reviews it; a request is not an approved schedule. |
| Claim an expense | Expense Claim | Add truthful items and receipts; approval and accounting follow the configured workflow. |
| Request money in advance | Employee Advance | Approval and accounting happen in standard ERPNext/HRMS. |
| View pay | Salary | Only submitted Salary Slips in a covering Payroll Period appear. |

When an employee opens a submitted payslip, the **Download PDF** action uses the native **Malaysia Payslip** print format. It shows the pay period, earnings, deductions, net pay and employee/employer statutory amounts in a compact A4 layout. Internal rule versions, source hashes, filing references, journal IDs and calculation explanations remain in Frappe HR for authorised payroll users and are not printed on the employee copy. Bank accounts are masked to the last four digits.

Submitting a request does not mean it is approved. Return to the same screen and check its status.

### 8.1 TP1 tax reliefs

An employee who wants eligible optional reliefs considered in PCB opens `/my-tax-reliefs/new`.

1. Confirm the prefilled tax year and declaration date.
2. Add one row per claim.
3. Select the controlled relief code.
4. Enter the amount and claim month from 1 to 12.
5. Attach the receipt or other evidence.
6. Tick the truth-and-completeness declaration.
7. Select the form's primary save/submit button and wait for the success message.

The button is labelled **Send for Review**. A successful handoff shows **Sent for Review** and moves the declaration to **Pending Review**. That means HR received it; it does not mean HR approved it. The declaration affects PCB only after HR selects **Approve** and it becomes a submitted Frappe document.

### 8.2 TP3 previous employment

An employee who received pay from another employer earlier in the same tax year opens `/my-previous-employment/new`.

1. Enter the previous employer and employment dates.
2. Copy gross regular pay, gross additional pay, EPF, PCB, Zakat and itemised prior TP1 reliefs from the signed TP3 evidence.
3. Attach the signed evidence.
4. Tick the declaration and select **Send for Review**.

Do not estimate missing values. Approved TP3 data affects cumulative PCB.

If there was more than one previous employer, create one TP3 per signed employer form. Never merge two employers into one record. Exact duplicate employer/period records are blocked, while all approved TP3 amounts are included in cumulative PCB. Prior TP1 reliefs must be itemised by controlled relief code; the combined annual limits apply across every TP3 and the current-employer TP1, and a legacy lump-sum amount is rejected.

## 9. HR Manager tax work

### TP1 and TP3

1. Open the declaration from the Workspace or Workflow Actions and confirm it is **Pending Review**. A Draft has not completed the employee handoff and must not be approved through a workaround.
2. Review every amount against the attachment.
3. Confirm the employee, Company and tax year are correct.
4. Check that evidence belongs to this employee, has not been reused and supports the stated amount.
5. For claims that need eligibility or sub-limit judgement, record specific review notes.
6. Select **Approve**, or **Return** it to the employee for correction.

Approval submits the document through Frappe's normal document lifecycle. The employee cannot approve their own declaration. Only one approved TP1 may exist for the employee, Company and tax year; TP3 permits separate, non-duplicate records for distinct previous employers and periods.

Returning is not rejection of the employee. It means the Draft needs correction. Tell the employee what to change; do not silently rewrite their declaration for them.

### CP38

Create a CP38 Directive only from a real LHDN instruction.

1. Select Employee and Company.
2. Enter the unique directive reference and effective dates.
3. Enter the directive total and monthly deduction.
4. Attach the LHDN directive.
5. Submit the document.

Salary Slip deducts no more than the remaining balance and records the amount used.

Before submission, compare Directive Amount, Monthly Deduction, Effective From and Effective To with the attached instruction. After each payroll, check Amount Deducted and Balance. Cancel/amend the record only through an approved correction process; never reduce the original directive amount merely to make the balance reach zero.

## 10. Attendance, leave, shifts and overtime

Keep all ordinary HR work in Frappe HR:

- Shift Type and Shift Assignment;
- Employee Checkin and Attendance;
- Attendance Request;
- Leave Policy and Leave Application;
- Expense Claim and Employee Advance;
- Employee Separation;
- recruitment, training and performance records.

For overtime, use standard HRMS Overtime Type and Overtime Slip. On each relevant Overtime Type, choose the added **Statutory Day Type**:

- Normal Overtime;
- Rest Day;
- Public Holiday.

The approved Overtime Slip creates normal Additional Salary. The localisation calculates the amount from the effective Contract, Salary Structure context and applicable full-time or part-time rule. It does not create a parallel overtime workflow.

### Daily manager routine

1. Review missing or unusual Employee Checkins.
2. Review Attendance and ensure approved leave is reflected correctly.
3. Process Attendance Requests using evidence and the configured approver; never self-approve your own correction.
4. Confirm Shift Assignments and approved Shift Requests in standard HRMS.
5. Review new Expense Claims and Employee Advances through their standard workflows.
6. Record unresolved items before payroll cutoff rather than fixing them inside Salary Slip.

### How overtime reaches payroll

1. The employee has submitted **Attendance** for the date and is marked Present.
2. Attendance contains the correct Overtime Type and duration from the standard HRMS process.
3. HR or payroll creates an **Overtime Slip** for the employee and period.
4. Overtime Slip loads the applicable Attendance records.
5. Review each date, day type, hours and calculated amount.
6. Submit Overtime Slip.
7. Standard HRMS creates the corresponding Additional Salary for payroll.

The app totals pending and submitted Overtime Slip detail by calendar month and blocks more than 104 hours. Creating several shorter Overtime Slips does not avoid the monthly limit.

### Leave and unpaid time

Use standard Leave Types, Leave Policies, Leave Allocations and Leave Applications. Complete approvals before payroll. Payroll should consume the standard attendance/leave outcome; this localisation does not maintain a second leave balance.

When an employee says pay is wrong because of leave, inspect in this order:

1. Leave Application dates and status;
2. Leave Type and whether it is paid or unpaid;
3. Attendance for the affected dates;
4. Salary Slip working days, payment days and leave without pay;
5. the earning formula and whether it depends on payment days.

### Expense claims are not salary earnings

Process ordinary business reimbursements through standard Expense Claim and accounting. Do not place a reimbursement into Salary Structure merely because it is convenient. If a payment is genuinely remuneration, use the approved Salary Component treatment and payroll process.

## 11. Run monthly payroll

Run payroll from a written cutoff calendar. A simple monthly rhythm is:

- **Before cutoff:** employees submit leave, claims and tax information; managers resolve attendance.
- **At cutoff:** stop ordinary backdated changes for the period and record any approved late exception.
- **Preparation day:** run Payroll Readiness, create Payroll Entry and draft Salary Slips.
- **Review day:** compare every employee and Company total with source records and the prior month.
- **Pay day:** submit/account through standard Frappe HR and complete the bank maker/checker process.
- **After pay:** prepare authority handoffs, upload/pay outside Frappe, attach evidence and reconcile.

Never promise a pay-day result until the draft has been reviewed. Readiness proves setup completeness, not the correctness of every ringgit.

### 11.1 Prepare the sources

Before creating payroll, verify:

- joiners, leavers, attendance, leave and unpaid days;
- effective Contract and Salary Structure Assignment;
- submitted Additional Salaries and Overtime Slips;
- approved TP1 and TP3;
- active CP38 and correct Zakat;
- complete statutory identities and any recorded LINDUNG 24 Jam liability release;
- Holiday List, Fiscal Year and Payroll Period;
- approved Salary Component treatment and accounts.

Use one payroll-control sheet or standard report containing, at minimum:

| Employee | Basic/recurring pay | Variable earnings | Unpaid days | Overtime | Zakat | CP38 | Expected unusual item | Checked by |
|---|---:|---:|---:|---:|---:|---:|---|---|

The control sheet is not a second payroll calculation. It tells the reviewer what changed and where to investigate.

### 11.2 Run Payroll Readiness

Open **Payroll Readiness**, select Company and payroll date, and run it. Resolve every problem at its source. The report checks setup; it does not approve legal eligibility or prove that pay amounts are correct.

Use **Show Ready Employees** only when you want the complete population. With it off, the report is an exception list. The Company setup row appears separately when HRD Corp configuration conflicts with employee headcount.

Run the report twice:

1. early enough to fix onboarding/setup issues before cutoff;
2. immediately before submitting Payroll Entry.

### 11.3 Use standard Payroll Entry

1. Create a normal Payroll Entry.
2. Select Company, posting date, payroll frequency, period, payable account and other normal filters.
3. Save and select **Get Employees**.
4. Confirm the employee list.
5. Select **Check Statutory Setup**.
6. Fix every employee-specific issue until the message says the setup is ready.
7. Select the standard **Create Salary Slips** primary action.
8. Confirm the action. In the pinned HRMS version, this submits Payroll Entry and its `on_submit` process creates the draft Salary Slips.
9. Wait for a queued run to finish when HRMS says creation is queued; do not start a second Payroll Entry.
10. Open the created draft Salary Slips and review them before using **Submit Salary Slip** on Payroll Entry.

The button is deliberately read-only: it does not create another payroll state, hash screen or release workflow.

What the actions mean:

- **Get Employees** fills the Payroll Entry employee table using the standard HRMS filters. Review the list; it is not proof that each employee is ready.
- **Check Statutory Setup** reads the selected employees and tells you which source record needs attention. It changes nothing.
- **Create Salary Slips** is the pinned HRMS primary action: it submits Payroll Entry, triggers the statutory readiness gate on the server and then creates the employee payroll documents. A user cannot bypass the gate by ignoring the readiness button.
- **Submit Salary Slip** appears after the Drafts exist. Use it only after the review in section 11.4. Malaysia calculations are applied while each draft Salary Slip validates.

If an employee should not be in the run, determine why before deleting the row. A wrong Company, status, date or payroll frequency may indicate a master-data issue affecting future periods too.

### 11.4 Review Salary Slips

On every draft Salary Slip, verify:

- employee, dates, payment days and unpaid days;
- every earning and Additional Salary;
- EPF employee and employer amounts;
- SOCSO and LINDUNG amounts;
- EIS employee and employer amounts;
- PCB, CP38 and Zakat;
- HRD employer levy where applicable;
- gross pay, total deductions and net pay.

Open **Earnings & Deductions → Statutory Contributions** for wage bases and employee/employer control totals. **Calculation Details** contains the rule-pack identifier for audit; routine users do not need to interpret a SHA-256 value.

When amounts are correct, submit Salary Slips and continue with normal Frappe HR accounting and the bank's approved maker/checker payment process.

#### Review one employee from top to bottom

1. Confirm Employee, Company, start date and end date.
2. Compare working days, payment days and leave without pay with approved attendance and leave.
3. Compare recurring earnings with Salary Structure Assignment.
4. Compare bonus, overtime, commission and other variable lines with submitted source records.
5. Check gross pay before looking at deductions.
6. Check each statutory wage base in **Statutory Results**. A wage base can legitimately differ between schemes, but the reason must be the approved component treatment.
7. Check employee deductions and employer contributions.
8. Compare PCB with prior-year/current-year declarations and year-to-date pay where relevant.
9. Check CP38 against the active directive balance and Zakat against the approved recurring or Additional Salary amount.
10. Check total deductions and net pay.
11. Compare with the prior month and explain every material difference.

#### Understand Statutory Results

| Scheme row | Employee amount | Employer amount | Extra amount |
|---|---|---|---|
| EPF | Employee EPF deduction | Employer EPF contribution | Normally zero |
| SOCSO | Employee SOCSO deduction | Employer SOCSO contribution | LINDUNG/SKBBK employee amount |
| EIS | Employee EIS deduction | Employer EIS contribution | Normally zero |
| PCB | Employee monthly tax deduction | Zero | Zero |
| CP38 | Additional employee tax collection | Zero | Zero |
| Zakat | Employee zakat deduction/rebate input | Zero | Zero |
| HRD Corp | Zero | Employer levy | Zero |

The ordinary Deductions table contains the employee-facing payroll deductions. The read-only Statutory Results table also carries employer amounts and calculation explanations for review.

#### Review the whole payroll

After individual checks:

1. total gross pay and net pay across all Salary Slips;
2. total each employee deduction and employer contribution;
3. compare employee count with active staff and the prior month;
4. compare total net pay with the bank instruction;
5. investigate every new employee, missing employee, leaver and large month-to-month movement;
6. have a named reviewer sign off before payment.

Do not submit a Salary Slip merely to see whether it works. Keep it Draft during review. Submission makes it an authoritative payroll result and later filings depend on it.

### 11.5 Finish standard payroll and accounting

Return to the submitted Payroll Entry and use **Submit Salary Slip** after review. Then use the standard accounting and bank-entry actions according to your configured process. Confirm:

- the payroll payable and expense accounts are correct;
- cost centres match the approved allocation;
- the accounting total agrees with submitted Salary Slips;
- the bank-payment total agrees with employee net pay;
- payment evidence and bank reconciliation are retained through the normal accounting process.

This localisation does not add a second release status. Use your standard Frappe Workflow, role permissions and bank maker/checker controls if the organisation requires formal payroll approval.

## 12. Prepare monthly authority files

Accounts Manager creates one **Statutory Filing** per Company, authority and exact payroll period.

1. Select EPF, PERKESO, LHDN or HRD Corp.
2. Enter Period Start and Period End.
3. Save the draft.
4. Select **Prepare File**.
5. Review every employee row and all control totals.
6. Download the output from the standard **Attachments** area.
7. Validate and upload it through the official portal.
8. Attach the real portal receipt under **Portal Submission Evidence**.
9. Submit the Frappe document. This records who prepared the evidence; it is not the government submission itself.
10. When the authority responds, attach the acknowledgement and set Authority Status to Accepted or Rejected.
11. Select **Reconcile** only after the accepted totals agree.

| Authority | Prepared artifact | Meaning |
|---|---|---|
| EPF | Private contribution CSV | i-Akaun preparation; requires current portal UAT |
| PERKESO | 278-character ASCII text file | Combined SOCSO, EIS and LINDUNG 24 Jam file defined by PERKESO; requires ASSIST UAT |
| LHDN | Fixed-width PCB/CP38 text file | Monthly preparation; requires current LHDN validator UAT |
| HRD Corp | CSV working paper | Levy reconciliation, not an automatic submission |

The fingerprints used to make generation retry-safe and detect changed Salary Slip inputs are internal hidden fields. Users work with the attachment, control totals, Frappe Version history and real authority evidence.

### Filing status in plain language

```text
Draft
    → Prepare File
    → review totals and download private attachment
    → validate/upload/pay in the official portal
    → attach portal receipt
    → Submit Frappe record (Authority Status remains Pending)
    → receive authority acknowledgement
    → attach acknowledgement and set Accepted or Rejected
    → Reconcile after Accepted totals agree
```

Submitting the Frappe record is not the same as submitting to the authority. Frappe has no proof of the external event until an authorised user attaches the actual evidence.

### EPF handoff

1. Create the filing with Authority = **EPF** and the exact Salary Slip period.
2. Prepare the file.
3. Compare employee EPF member number, identity, wage, employee contribution and employer contribution with the reviewed Salary Slips.
4. Download the private CSV from Attachments.
5. Validate it using the current EPF i-Akaun process approved during UAT.
6. Upload and pay outside Frappe.
7. Attach the real receipt, submit the Frappe filing and later attach the acknowledgement.
8. Mark Accepted and Reconcile only when the portal and Frappe totals agree.

### PERKESO handoff

1. Create the filing with Authority = **PERKESO**.
2. Prepare the file.
3. Review SOCSO, EIS and LINDUNG/SKBBK amounts for each employee.
4. Download the `.txt` attachment. Text is intentional: this adapter prepares the reviewed 278-character combined ASCII record format.
5. Do not open and resave the file in a word processor or spreadsheet; that can change spacing, line endings or encoding.
6. Validate it in the current ASSIST process approved during UAT.
7. Upload/pay, attach real evidence, submit the Frappe record, record the response and reconcile.

A `.txt` extension alone does not prove compliance. Only successful validation against the current official portal/specification during UAT does.

### LHDN handoff

1. Create the filing with Authority = **LHDN**.
2. Prepare the fixed-width PCB/CP38 text file.
3. Compare each TIN, NRIC, employee number, PCB and CP38 amount with the Salary Slips and active directives.
4. Validate and submit using the current LHDN process approved during UAT.
5. Attach the receipt, submit the Frappe record and later attach the acknowledgement.
6. Mark Accepted and Reconcile only when totals agree.

### HRD Corp working paper

1. Create the filing with Authority = **HRD Corp**.
2. Prepare the CSV.
3. Review leviable wages and employer levy by employee.
4. Reconcile the total with the Company's effective registration class.
5. Use the current HRD Corp payment/submission process outside Frappe.
6. Retain payment/submission evidence and reconcile the Frappe filing.

This CSV is a working paper, not a claim that HRD Corp accepts a particular upload format.

### If Prepare File says the source changed

The system includes every value that affects serialization—Company identifiers, employee identifiers, contribution results, period and rule version—in its source fingerprint. If any of those changes:

- while the filing is Draft, run **Prepare File** again and repeat the review;
- after the filing is Submitted, preserve it and create the required amendment;
- never upload an older attachment after the source-change warning.

### Deadlines

Create a recurring calendar or Frappe task for each authority's current payment and submission deadline. This app prepares payroll data; it does not guarantee that a changing statutory deadline is configured or that a portal was available. The accountable operator must verify deadlines against current official guidance.

## 12A. Reports for review

### Malaysia Payroll Readiness

Use before Payroll Entry. It reports missing Company or employee setup. It is not a payroll preview and does not calculate expected net pay.

### Malaysia Annual Remuneration

Select only a Company you are authorised to read and the required year. The report totals submitted Salary Slips by employee for gross pay, net pay, EPF, SOCSO, EIS, PCB, CP38 and Zakat. Employees on `SOCSO + EIS — LINDUNG Optional` are omitted unless you tick **Show All Statutory Profiles**. Use it for internal reconciliation and annual preparation; it is not itself an EA form or an authority submission.

Export payroll reports only when necessary. Store exported files securely because they contain employee pay and identity-related data.

## 12B. Joiners, pay changes and leavers

### Mid-month joiner

1. Set the true Date of Joining on Employee.
2. Ensure the Contract and Salary Structure Assignment are effective from the correct date.
3. Assign the correct Holiday List.
4. Complete statutory identifiers before payroll cutoff.
5. Run Readiness for the payroll date.
6. Review the Salary Slip's working days, payment days and prorated earnings independently.

Do not alter the joining date merely to obtain a desired proration.

### Pay rise or contract change

1. Preserve the old Contract and assignment history.
2. Create the new effective Contract or standard amendment required by the Company's process.
3. Create a new Salary Structure Assignment from the approved effective date.
4. Recheck Salary Component treatment if a new earning is introduced.
5. Test the first affected Salary Slip and compare it with the approved pay-change letter.

### Leaver

Use standard Employee Separation and the Company's approved termination process.

1. Record the true relieving date and complete attendance/leave through the last day.
2. Resolve approved overtime, Additional Salary, expense claims, advances and recoveries.
3. Determine final-pay items and timing with qualified Malaysian review; do not assume an ordinary full-month payroll is sufficient.
4. Create and independently review the final Salary Slip.
5. Complete required LHDN or other authority notifications outside this phase-1 app where no implemented, reviewed adapter exists.
6. Disable system access at the approved time without deleting the Employee or payroll history.
7. Retain records according to the Company's legal retention and privacy policy.

The phase-1 localisation does not automate every commencement, cessation, death, departure or final-pay form. Absence of a screen does not remove the employer's obligation.

### Off-cycle payroll

Use standard HRMS off-cycle Payroll Entry/Salary Slip procedures only after deciding why the amount cannot wait for the next regular payroll. Include all submitted slips ending in the same month when reconciling statutory totals; the localisation calculates month-to-date deltas to avoid charging a monthly contribution twice.

Check an off-cycle run especially carefully for:

- additional-remuneration PCB treatment;
- same-month EPF, SOCSO, EIS and LINDUNG totals;
- CP38 monthly remaining amount;
- whether the authority handoff period includes both regular and off-cycle slips.

## 12C. Operating calendar

### Every working day

- managers review attendance exceptions and leave requests;
- employees submit truthful claims and requests;
- HR records joiners, leavers and approved changes at the source;
- access or privacy incidents are escalated immediately.

### Every payroll month

- close attendance and variable-pay inputs;
- run Readiness;
- prepare and review payroll;
- complete bank payment through approved controls;
- prepare, submit and reconcile each statutory obligation;
- store evidence and investigate exceptions.

### Every year or rule change

- create Fiscal Year and Payroll Period;
- update Holiday Lists;
- install and validate a rule pack reviewed for the new dates;
- review TP1/TP3 processes and payroll component treatment;
- reconcile annual remuneration;
- retest authority adapters and permissions;
- test backup restoration.

## 13. Corrections

Before Salary Slip submission, correct the authoritative Employee, Contract, Salary Structure Assignment, Attendance, Leave, Additional Salary, TP1, TP3 or CP38 record and regenerate the draft.

After submission, use standard Frappe cancellation and amendment procedures. Never edit database values or add an unexplained balancing component.

After a Statutory Filing is submitted, preserve the original attachment and evidence. Follow the authority's amendment process and create an amended Frappe document; do not rewrite history.

Use this decision table:

| Problem found | Correct action |
|---|---|
| Draft Salary Slip is wrong | Correct its authoritative source, then regenerate or recalculate the Draft and repeat review. |
| Submitted Salary Slip is wrong but not filed | Stop payment where possible; use approved cancel/amend controls and repeat accounting review. |
| Submitted Salary Slip is already in a submitted filing | Preserve both records; follow payroll and authority amendment procedures. The app blocks casual cancellation of a filed slip. |
| Draft filing source changed | Select Prepare File again, then re-review the new attachment and totals. |
| Submitted filing source changed | Create an amendment; never replace the original evidence. |
| Authority rejects a file | Record Rejected, retain the message, correct the source/adapter through an approved process and create the required amendment. |
| Bank paid a wrong amount | Escalate immediately through accounting/bank controls; do not conceal it with next month's Salary Slip. |

Every correction should answer four questions: what was wrong, which source was corrected, who approved it, and how the corrected total was verified.

## 14. Monthly checklist

### Payroll

- [ ] Employee changes, attendance and leave are complete
- [ ] Contracts and Salary Structure Assignments are effective
- [ ] Additional Salary and Overtime Slips are submitted
- [ ] TP1, TP3, CP38 and Zakat are current
- [ ] Payroll Readiness has no unexplained issue
- [ ] Payroll Entry employee list and dates are correct
- [ ] Check Statutory Setup says ready
- [ ] Every draft Salary Slip is checked against the approved source
- [ ] Salary Slips are submitted
- [ ] Standard accounting and bank maker/checker process is complete

### Authorities

- [ ] EPF employee and control totals agree
- [ ] PERKESO SOCSO, EIS and LINDUNG totals agree
- [ ] LHDN PCB and CP38 totals agree
- [ ] HRD levy agrees where registered
- [ ] Each output passes the current official validator
- [ ] An authorised human uploads and pays it
- [ ] Real receipt and acknowledgement are attached privately
- [ ] Accepted filing is reconciled

### Employee access

- [ ] Every active employee can sign in to HRMS
- [ ] Each employee sees only their own information
- [ ] Submitted Salary Slips appear in Salary
- [ ] Pending leave, attendance and expense requests have an approver
- [ ] Leavers' access is disabled at the approved time

## 15. Security and privacy for ordinary users

Payroll contains some of the Company's most sensitive data. Follow these rules even in a very small team:

- everyone uses their own account;
- privileged users enable MFA;
- employees receive Employee Self Service, not HR Manager or Accounts roles;
- Company User Permissions limit managers, payroll users, Accounts Managers and Auditors to their real Company;
- attachments containing NRIC, TIN, bank, tax or authority data are private;
- exported spreadsheets and downloaded authority files are removed from uncontrolled Downloads folders according to the retention procedure;
- no one sends payroll files through personal messaging accounts;
- permission access is reviewed when a person changes job or leaves;
- backups are encrypted and a full restore is tested, not merely assumed;
- suspected disclosure, wrong-recipient email or unauthorised access is escalated through the Company's Malaysian privacy/breach procedure.

The Auditor role is read-only, but it still exposes sensitive data. Give it only to named people with a real audit need and Company User Permission.

## 16. Troubleshooting

| What you see | Meaning | What to do |
|---|---|---|
| `500` and Redis connection refused | The test/production Bench is incomplete | Start the complete Bench services; do not change payroll data |
| Employee lands in Desk | The login redirect did not target HRMS | Open `/hrms/home` directly or use `/login?redirect-to=/hrms/home` |
| Invalid or missing employee | User is not linked to one Active Employee | Correct Employee User ID, status and Employee Self Service user type |
| No salary slips in HRMS | Slip is draft, link is wrong or Payroll Period is missing | Submit the correct slip and create the covering Payroll Period |
| TP1/TP3 stays Draft or no **Sent for Review** page appears | The handoff failed before Frappe applied the Workflow action | Keep the Draft, copy the visible error, and ask the administrator to check the web worker/error log; do not edit workflow state in the database |
| Earning component has no Statutory Treatment | A payable earning has blank PCB classification | Open the named Salary Component, obtain approved treatment and save it |
| Statutory setup needs attention | Employee, Contract, Holiday List or Fiscal Year is incomplete | Fix the named source record and run the check again |
| Company setup says HRD registration conflicts | Active Malaysian headcount and Company HRD class disagree | Verify real registration status, then correct Company or employee records; do not pick a class merely to unblock payroll |
| LINDUNG release incomplete | A release is missing evidence/registration date, falls outside its window, or the employee has multiple employers | Correct the source evidence; phase 1 does not automate multiple-employer selection |
| Rule pack expired | Payroll date is later than the reviewed rules | Install a newly reviewed release; never bypass the date |
| Overtime exceeds 104 hours | All pending/submitted Overtime Slip details in that calendar month exceed the limit | Review duplicate/wrong attendance and overtime records; do not split the hours across slips |
| Prepare File is absent | Filing is final or the user is read-only | Use Accounts Manager or follow the amendment process |
| PERKESO output is `.txt` | The official combined batch specification is fixed-width text | Preserve encoding/spacing and validate it in ASSIST |
| Filing says payroll results or identifiers changed | A serialized Company/Employee identity or Salary Slip result changed after preparation | Prepare again if Draft; create an amendment if Submitted |
| Reconcile is blocked | Evidence, authority status, totals or source data do not agree | Investigate; attach real evidence or create an amendment |

### How to report a problem

Give support the following without exposing unnecessary personal data:

1. your user role, not your password;
2. the screen name and record ID;
3. the exact action selected;
4. the exact error message and time;
5. whether the record was Draft or Submitted;
6. whether the same issue occurs after a normal page reload.

Never send a database dump, private attachment, NRIC or password in an ordinary chat message.

## 17. What the app deliberately does not add

- another employee profile;
- another employment agreement;
- another Payroll Entry or release state;
- custom recruitment, attendance, leave, claims, shifts or performance;
- an employee portal or design system;
- a bank payment uploader;
- an authority login robot;
- unsupported foreign-worker, East Malaysian or specialist-tax estimates.

“Complete” means the standard Frappe HR payroll is correct, accounting and salary payment follow approved controls, every authority total agrees, a human completed the official submission, and the real evidence is retained. Automation does not remove the employer's legal accountability.
