# Malaysia Payroll: user guide

This is the handbook for people who use Malaysia Payroll on Frappe HR. Open only the chapter for your job.

| I am… | Read |
|---|---|
| **New here** | [How the system works](#how-the-system-works) |
| **Employee** | [Employee](#employee) |
| **HR Manager** | [HR Manager](#hr-manager) |
| **Accounts Manager** | [Accounts Manager](#accounts-manager) |
| **Auditor** | [Auditor](#auditor) |
| **System Manager** | [System Manager](#system-manager) |
| **Running this month's payroll** | [Monthly checklist](#monthly-checklist) |
| **Stuck** | [When something goes wrong](#when-something-goes-wrong) |

Use Frappe HR for ordinary HR (leave, attendance, pay run, accounting). Use this app only for Malaysian statutory details, calculations, TP1/TP3/CP38 and authority file preparation.

It does **not** replace Employee, Contract, Salary Structure, Payroll Entry, Salary Slip, or the Frappe HR mobile app.

---

## How the system works

Pay is built in order. If a number is wrong, fix the earlier record. Do not type a balancing figure into a Salary Slip.

```text
Company and pay rules (once)
    → Employee + Contract + salary assignment
    → this month's attendance, leave, overtime, one-off pay
    → Payroll Readiness (fix every red item)
    → Payroll Entry → Salary Slip
    → pay the staff through your bank
    → prepare EPF / PERKESO / LHDN / HRD files
    → a person uploads them to the government portal and keeps the receipt
```

**What the software does:** calculate reviewed EPF, SOCSO, LINDUNG 24 Jam, EIS, PCB, CP38, zakat and HRD amounts, and prepare a file.

**What a person still does:** decide if a declaration is true, upload to the government portal, pay the bank, and store the real receipt. A file attached in Frappe means “prepared here,” not “accepted by LHDN or EPF.”

Phase 1 is for **Peninsular Malaysia** and Malaysian citizens or permanent residents under ordinary resident PCB. Unsupported cases stop instead of guessing.

### Where you work

| Who | Open |
|---|---|
| Employee | `/login?redirect-to=/hrms/home` on a phone or computer |
| Employee, optional tax reliefs (TP1) | `/my-tax-reliefs/new` |
| Employee, previous employer this year (TP3) | `/my-previous-employment/new` |
| Everyone else | Desk → search **Malaysia Payroll**, or `/app/malaysia-payroll` |

Give each person only their link. Do not ask staff to use the wide Desk screen on a phone.

If you cannot find a screen: Desk search box → type the **bold** name from this guide. If it does not appear, your role or Company permission is wrong. Do not borrow someone else's login.

### Four Frappe words

| Word | Meaning |
|---|---|
| **List** | Many records. Filter, then click one. |
| **Form** | One record. |
| **Save** | Keep a draft. You can still change it. |
| **Submit** | Lock it as the official record. To correct it, cancel and amend — do not edit around it. |

Draft = still working. Submitted = relied upon. Cancelled = reversed but kept. An orange **Not Saved** dot means save before you leave.

### Malaysian payroll words

| Term | In this system |
|---|---|
| **EPF / KWSP** | Retirement fund. Employee deduction + employer cost. |
| **PERKESO / SOCSO** | Social security. Employee + employer. |
| **EIS** | Employment insurance. Employee + employer. |
| **LINDUNG 24 Jam** | Extra PERKESO employee amount (on by default from 1 June 2026). |
| **PCB / MTD** | Monthly tax the **company** must deduct and pay to LHDN. |
| **TP1** | Optional. Employee asks HR to use extra tax reliefs in monthly PCB. Most small companies never use this. |
| **TP3** | Previous employer's figures in the **same tax year**. Needed only for mid-year joiners. Copy them; do not guess. |
| **CP38** | Extra tax cut from a specific LHDN letter. Not ordinary PCB. |
| **Zakat** | Employee deduction; also used as a PCB rebate input. |
| **HRD Corp** | Employer-only levy. |

The employee's **yearly** tax return is still their job with LHDN. PCB is the company's monthly collection duty.

---

## Employee

You use Frappe HR on your phone or computer. You should not need Desk.

### First sign-in

1. Open the HRMS link your company sent.
2. Sign in with **your** email and password.
3. Open **Profile**. The name must be yours. If it is someone else, sign out and tell HR.
4. Open **View Salary Slips** from home (do not type `/hrms/home/salary` — that page can be blank).
5. Open **Leaves**, **Attendance** and **Expenses** so you know where they are.
6. Sign out and sign in once more to confirm the password.

No payslips before the first completed payroll is normal.

### Everyday tasks

| I need to… | Use | Then |
|---|---|---|
| Take leave | Leave Application | Wait for approval. A request is not approved leave. |
| Fix a missing punch | Attendance Request | Explain what is wrong. Wait for approval. |
| Change a shift | Shift Request | A request is not an approved roster. |
| Claim an expense | Expense Claim | Attach real receipts. |
| Ask for an advance | Employee Advance | Follow company approval. |
| See my pay | **View Salary Slips** | Download PDF after payroll is submitted. |

The PDF is the **Malaysia Payslip**: period, earnings, deductions, net pay, and employee/employer statutory amounts. Bank account is masked to the last four digits. Internal hashes and journal IDs are not printed.

### Optional: TP1 (monthly tax reliefs)

You do **not** have to do this. Many companies never use TP1. You can claim those reliefs on your own LHDN e-Filing instead.

Use it only if HR asked you to, and you want extra reliefs (lifestyle, books, and similar) already considered in **monthly** PCB.

1. Open `/my-tax-reliefs/new`.
2. Keep the tax year and date if they look right.
3. Add one row per claim: relief code, amount, month (1–12), receipt.
4. Tick “I declare that this information is true and complete.”
5. Select **Send for Review**.

**Sent for Review** means HR received it. It is not approved yet. It affects pay only after HR selects **Approve**.

### Only if you joined this year from another employer: TP3

If another employer already paid you in this tax year:

1. Open `/my-previous-employment/new`.
2. Copy amounts from the **signed TP3**, not from memory: employer name, dates, gross pay, extra pay, EPF, PCB, zakat, and any prior TP1 reliefs.
3. Attach the signed TP3.
4. Tick the declaration and **Send for Review**.

One TP3 per previous employer. Do not merge two employers. Do not invent missing numbers.

### Never

- Share your password.
- Claim another person's relief.
- Guess TP3 figures.

---

## HR Manager

Desk search **Malaysia Payroll**. That workspace is your home: setup records, tax records, payroll, and filings (read-only).

### Your job

Keep employee facts and contracts true, review TP1/TP3 evidence if anyone submits them, record CP38 from a real LHDN letter, run readiness, prepare Payroll Entry, and check every Salary Slip **before** it is submitted.

You do not upload EPF/LHDN files. That is Accounts Manager.

### Add a person (in this order)

A saved Employee is not payroll-ready by itself.

```text
User login (Employee Self Service)
    → Employee + Statutory Details
    → active Contract
    → Salary Structure + Salary Structure Assignment
    → Payroll Readiness says Ready
```

**Login**

1. Create a User with the person's own email.
2. Create the Employee and set **User ID** to that User.
3. User Type = **Employee Self Service**. No HR, Accounts, or System Manager roles.
4. Ask them to sign in to HRMS the same day.

**Employee → Statutory Details**

- Citizenship, NRIC.
- Date of Birth (this sets SOCSO Category and EIS Eligible automatically; you do not type those).
- For ordinary staff (**Standard Payroll**): TIN, EPF member number, PCB resident, PCB Category (1 Single / 2 Married spouse not working / 3 Married spouse working), child units, disability flags.
- LINDUNG 24 Jam stays **Participating** unless the employee personally filed a PERKESO Liability Release Notice. The company cannot file that notice for them.

**Contractor (SOCSO + EIS only):** set **Statutory Profile** to `SOCSO + EIS — LINDUNG Optional`. Fill NRIC. Leave TIN, EPF, PCB, TP1, TP3 and CP38 blank. They still need a Contract and salary assignment. They appear on PERKESO filings, not EPF, LHDN or HRD.

**Contract → Statutory Working Terms** (open Contract from the Malaysia Payroll **Setup** card, not by hunting in CRM)

- Wage basis: Monthly, Daily or Hourly.
- Full-time or part-time.
- Daily/hourly rate if not monthly.
- Normal hours per day and week.
- Rest day.
- Overtime eligible.

**Pay**

- Every earning **Salary Component** needs **Statutory Treatment** (which schemes it counts for, and **PCB Treatment**). Ignore HRMS “Is Tax Applicable” for Malaysian PCB — use **PCB Treatment**.
- Submit Salary Structure, then Salary Structure Assignment with the real start date and base.
- One-off bonus or allowance: **Additional Salary**, not a typed line on a submitted slip.
- Overtime: HRMS **Overtime Type** with **Statutory Day Type** (Normal Overtime / Rest Day / Public Holiday), then **Overtime Slip**. Ignore the HRMS holiday/weekend multiplier boxes for statutory overtime. The month cannot exceed 104 hours of ordinary overtime across slips.

Then run **Malaysia Payroll Readiness**. Red means stop and fix the named record.

### Daily

1. Missing or odd check-ins.
2. Attendance and approved leave agree.
3. Attendance Requests, Shift Requests, Expense Claims — never approve your own.
4. Note anything still open before payroll cutoff.

### TP1 / TP3 review (only if someone sent one)

1. Open it from Malaysia Payroll. It must be **Pending Review**. Do not approve a Draft by a workaround.
2. Match every amount to the attachment.
3. Evidence must belong to this person and support the amount.
4. If a code needs judgement, write notes in **Employer Review**.
5. **Approve** or **Return**. Return means “please correct,” not “you are fired.” Tell them what to change. Do not silently rewrite their form.

You may **Send for Review** on behalf of someone with no self-service access. That still does not skip Approve.

One approved TP1 per employee, company and tax year. TP3: one record per previous employer.

### CP38

Only from a real LHDN letter. Employee, unique reference, dates, total, monthly amount, attach the letter, Submit. After payroll, check Amount Deducted and Balance. Never reduce the original total just to make the balance zero.

### Monthly payroll

1. Cutoff: no more casual backdated changes.
2. **Malaysia Payroll Readiness** for the company and payday. Empty-looking “Ready / nothing needs attention” is success. Tick **Show Ready Employees** to see everyone.
3. **Payroll Entry**: company, dates, Get Employees.
4. **Check Statutory Setup**. Wait until it says setup is ready. The button does not change data.
5. **Create Salary Slips**. In this Frappe HR version that **submits** Payroll Entry and then creates draft slips. Do not click twice.
6. Open each draft **Salary Slip**. Check the **Statutory** tab (EPF, SOCSO, LINDUNG, EIS, PCB, CP38, zakat, HRD).
7. A second person should review totals. The preparer should not be the only releaser.
8. **Submit Salary Slip** only after that review.
9. Accounting and bank payment stay in standard Frappe / your bank. This app does not send money.

Readiness checks **setup**. It does not prove every ringgit is correct.

### Joiners, rises, leavers

- Joiner: true joining date, contract and assignment from that date, identifiers before cutoff, then Readiness.
- Pay rise: new assignment from the effective date. Do not overwrite history.
- Leaver: relieving date, last attendance, final slip. Phase 1 stops PCB if the person leaves before 31 December of the tax year (annual projection would be wrong).

### Daily and Hourly base pay, and unworked public holidays

Base pay for Daily- or Hourly-rated staff is calculated by the HRMS Salary Structure, not this app. This app adds statutory deductions and the premium for a public holiday actually **worked**.

A gazetted public holiday they **do not** work is a separate Employment Act entitlement. Monthly staff already have it in the fixed salary. For Daily/Hourly staff it depends on how you built the Salary Structure. Readiness flags those employees for you to confirm; the system will not guess.

### Never

- Edit a submitted Salary Slip to force a net pay.
- Accept TP1/TP3 without evidence.
- Use another person's login.

Deeper setup of components, accounts and overtime masters: [Configuration](CONFIGURATION.md). Month-end operations summary: [Operations](OPERATIONS.md).

---

## Accounts Manager

You prepare government files **after** Salary Slips are submitted. You upload them on the official portal yourself.

Desk → **Malaysia Payroll** → **Statutory Filings**.

### One filing per company, authority and pay period

Authorities: **EPF**, **PERKESO**, **LHDN**, **HRD Corp**.

1. New filing: Company, Authority, Period Start, Period End. Save.
2. **Prepare File** (HRD Corp: **Prepare Working Paper**).
3. Read every employee row and the control totals. They must match the Salary Slips.
4. Download the private file from the form.
5. Validate and upload it in the **current official portal**. Pay there if required.
6. Attach the real portal receipt under **Portal Submission Evidence**.
7. **Submit** the Frappe record. That records who locked it here. It is **not** the government submission.
8. When the authority replies, attach the acknowledgement and set **Portal Status** to Accepted or Rejected.
9. **Reconcile** only after Accepted and the totals agree.

| Authority | What you get | Take it to |
|---|---|---|
| EPF | CSV | i-Akaun (after your UAT) |
| PERKESO | `.txt` (fixed-width on purpose) | ASSIST. Do not open it in Word or Excel. |
| LHDN | Text file for PCB/CP38 | Current LHDN validator |
| HRD Corp | CSV working paper | Your HRD payment process — not an auto-upload format |

**Draft** = still preparing in Frappe. **Submitted** = locked here. **Portal Status** = whether the government accepted the file.

If Prepare File says the source changed: Draft → prepare again. Already Submitted → amend; do not upload the old file.

Never mark **Accepted** without the real acknowledgement.

Accounting, bank files and salary payment stay in standard ERPNext. This app does not generate a bank bulk-payment file.

---

## Auditor

You are read-only. You can open records and reports. You cannot Save, Prepare, Submit or Reconcile.

### Look at

- Malaysia Payroll workspace
- Payroll Entry and Salary Slips (including the **Statutory** tab)
- TP1, TP3, CP38
- Statutory Filings: employee totals, prepared file, portal evidence, acknowledgement, Portal Status
- **Malaysia Payroll Readiness** and **Malaysia Annual Remuneration**

Annual Remuneration totals submitted slips for the year. Contractors on the SOCSO+EIS profile are hidden unless you tick **Show All Statutory Profiles**. It is not an EA form.

### Never

- Log in as HR or Accounts “just to help edit.”
- Export payroll spreadsheets onto an uncontrolled computer.

---

## System Manager

You install and look after the site. You do not run monthly payroll as Administrator.

### Once

Follow [Installation](INSTALLATION.md) and [Configuration](CONFIGURATION.md). In short:

1. Pinned Frappe, ERPNext and HRMS versions, then this app; migrate twice; build assets.
2. Time zone `Asia/Kuala_Lumpur`, country Malaysia, currency MYR.
3. Fiscal Year, Holiday List, Payroll Period (employees cannot see payslips in HRMS without a covering Payroll Period).
4. Payroll Settings: enable **Include holidays in Total no. of Working Days**.
5. Company → **Statutory Payroll**: enable it, Peninsular Malaysia, SSM, LHDN HQ and employer numbers, Company Tax ID (employer TIN), EPF employer number, PERKESO employer code, truthful HRD class.
6. Named users: System Manager, HR Manager, Accounts Manager, Auditor, Employee Self Service. Company User Permissions. MFA for privileged users.
7. HTTPS, encrypted backups, a tested restore, private files for NRIC/TIN/payroll.

Do not patch Frappe, ERPNext or HRMS core.

### Company HRD class

- **Compulsory (1%)** if that is the real registration.
- **Optional (0.5%)** only if optional registration was completed.
- **Not Registered** only if that is true.

The app blocks obvious conflicts (for example ten Malaysian employees while marked Not Registered). It cannot register the company for you.

### Never

- Use Administrator for daily HR.
- Promote a staging site to live payroll until the gates in [Validation](VALIDATION.md) pass.

---

## Monthly checklist

Keep this open during payroll.

**Before cutoff**

- [ ] Joiners, leavers, attendance, leave and overtime are complete
- [ ] Contracts and salary assignments are effective
- [ ] Additional Salary submitted
- [ ] TP1/TP3 approved only if someone actually filed them
- [ ] CP38 and zakat are current
- [ ] Every active employee can sign in to HRMS and sees only themselves

**Payroll**

- [ ] Payroll Readiness has no unexplained red item
- [ ] Payroll Entry dates and employee list are right
- [ ] Check Statutory Setup says ready
- [ ] Every draft Salary Slip checked on the Statutory tab
- [ ] A second person reviewed totals
- [ ] Salary Slips submitted
- [ ] Accounting and bank maker/checker done

**After pay**

- [ ] EPF, PERKESO, LHDN (and HRD if registered) files prepared
- [ ] Totals match Salary Slips
- [ ] Files passed the current official validator
- [ ] A named person uploaded and paid
- [ ] Real receipts attached, Portal Status set, Accepted filings reconciled
- [ ] Leaver logins disabled when they should be

---

## When something goes wrong

Correct the **source**, then regenerate the draft. After Submit, use Frappe cancel/amend. After a filing is submitted, keep the old evidence and amend.

| Problem | Do this |
|---|---|
| Draft Salary Slip is wrong | Fix Employee / Contract / attendance / Additional Salary / TP1 / CP38, then recalculate. |
| Submitted slip, not yet in a filing | Stop payment if you can; cancel/amend through Frappe; re-review accounting. |
| Slip already in a submitted filing | Keep both records; follow payroll and authority amendment. Casual cancel is blocked. |
| Draft filing, source changed | Prepare File again. |
| Submitted filing, source changed | Amend. Do not swap the old attachment. |
| Authority rejects the file | Portal Status = Rejected, keep the message, fix source, amend. |
| Bank paid the wrong amount | Escalate through accounts. Do not hide it in next month's slip. |

| What you see | Meaning | What to do |
|---|---|---|
| Employee lands in Desk | Wrong login link | Use `/hrms/home` |
| No payslips in HRMS | Draft slip, wrong User ID, or no Payroll Period | Submit the slip; create a covering Payroll Period |
| TP1 stays Draft | Send for Review did not finish | Keep the Draft; give the error to System Manager; do not edit workflow in the database |
| Setup needs attention | A named record is incomplete | Open that Employee, Contract or Salary Component and fix it |
| LINDUNG release incomplete | Missing notice, wrong window, or multiple employers | Fix evidence. Phase 1 will not guess the PERKESO-selected employer |
| Overtime exceeds 104 hours | Too many ordinary overtime hours in that calendar month | Fix the slips. Splitting across documents does not help |
| Prepare File missing | You are not Accounts, or the filing is already final | Use Accounts Manager, or amend |
| Reconcile missing | Portal Status is not Accepted, or you are read-only | Attach real acceptance first |

When you report a problem, send: your role (not password), screen name, record ID, the button you pressed, the exact message and time, Draft or Submitted. Never send NRIC, dumps or passwords in chat.

---

## LINDUNG 24 Jam (HR)

Default is **Participating** from 1 June 2026. Record **Not Participating** only with the employee's own Liability Release Notice, PERKESO registration date, and effective date.

- Existing employees could decline only 13 July–31 August 2026.
- A new local hire has 30 days from PERKESO registration.
- Multiple employers: tick the flag; payroll stops rather than guessing.
- June 2026 contributions are mandatory and not refundable.
- Timing follows the payroll run: record the release before you submit that month's slips if that month should already stop.

---

## What this app does not do

It does not add a second employee portal, a second employment contract, a second payroll run, a bank uploader, or a robot that logs into EPF or LHDN.

“Done” means: Frappe HR payroll is correct, staff are paid through your bank controls, authority totals agree, a human uploaded the official file, and the real receipt is stored.

The employer remains legally accountable. Get periodic Malaysian payroll and employment-law review.

First-time technical setup: [Installation](INSTALLATION.md), [Configuration](CONFIGURATION.md). Statutory scope: [Legal and statutory](LEGAL_AND_STATUTORY.md). Security: [Security](SECURITY.md).
