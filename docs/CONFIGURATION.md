# Configuration

## 1. Company

For each Malaysian company:

- Country: Malaysia
- Default Currency: MYR
- Enable Malaysia Payroll: enabled
- LHDN HQ Number
- LHDN Employer Number
- EPF Employer Number
- SOCSO Employer Code
- SSM / Company Registration Number
- Peninsular Malaysia jurisdiction and supported citizenship policy
- HRD Corp registration number and 1% levy rate for this 10+ employee deployment
- statutory rule-review deadline
- bank adapter key, bank UAT evidence and production activation evidence
- versioned Malaysia employee privacy notice
- verified encrypted backup timestamp/evidence and last successful restore-test date
- Default Payroll Payable Account in Frappe HR

Use separate companies for separate legal employers. Do not reuse one statutory employer number across unrelated Company records.

Publish the employer-approved privacy notice as a private standard File. Use a standard authenticated Web Form/Workflow on Employee to attach acknowledgement evidence; the hook records notice version, user and time immutably. Changing the Company notice version requires fresh acknowledgements before production reactivation.

## 2. Malaysia Workforce Settings

Review every field before production:

### Staffing and attendance

- Thirty-minute staffing slots, 4-hour preferred and 2-hour normal minimum assignments.
- Fourteen-day planning and availability/reminder deadlines.
- A standard base casual `Shift Type`; managed time variants clone its auto-attendance settings.
- Check-in windows and automatic verification tolerance.
- Whether verified work records are automatically submitted.

### Statutory controls

- `strict_rule_review` should remain enabled.
- Set `rules_reviewed_through` only after payroll/legal review of current tables and specifications.
- Choose the interim PCB method for non-final pay runs.
- Verify all Salary Component links.

### Employer accounting

Map valid non-group accounts belonging to the same company:

- Employer EPF Expense / EPF Payable
- Employer SOCSO Expense / SOCSO Payable
- Employer EIS Expense / EIS Payable
- HRD Corp Levy Expense / HRD Corp Levy Payable

Disable automatic Journal Entry creation until mappings are tested.

### Submission

Review official portal URLs. Leave API mode disabled unless an authority has formally provisioned an interface and credentials.

## 3. Salary Components

Each earning must be independently classified for:

- EPF wages
- SOCSO wages
- EIS wages
- PCB remuneration
- PCB remuneration type: regular, additional, benefit in kind, perquisite or not applicable
- HRD Corp levy wages
- legal authority for every deduction

Do not infer statutory treatment from the component name. Review allowances, overtime, arrears, bonuses, commissions and benefits with your Malaysian payroll adviser.

## 4. Employee profile

Create one effective profile containing identity and statutory registration data:

- NRIC or passport and passport country code
- nationality status
- tax number, residence, category and regime
- EPF, SOCSO and EIS numbers
- disability and child-unit fields
- SOCSO category and EIS eligibility
- LINDUNG designation where another employer is involved

Identity fields are normalised and duplicate active identities are rejected.

## 5. Work agreement

Create an effective-dated agreement for each employee. Do not overwrite a historical agreement after payroll use.

For casual workers typically use:

- Work Arrangement: Casual
- Contract Relationship: according to the actual legal relationship
- Regularity: Occasional or Irregular where accurate
- Pay Basis: Hourly
- Base Hourly Rate
- Normal and maximum hours
- Comparable full-time hours
- Minimum shift length
- Rest day
- Split-shift permission
- Branch and Shift Location

The app warns or blocks overlapping agreements, rates below the configured minimum and invalid hour limits.

## 6. Statutory coverage profile

Create an effective-dated profile containing all five schemes:

- EPF
- SOCSO
- EIS
- PCB
- LINDUNG 24 Jam

Available treatment values:

- Automatic
- Applicable
- Not Applicable
- Pending Review

`Not Applicable` requires an HR Manager/System Manager, a controlled reason, detailed notes and attached approval evidence. The actor and effective change are retained in immutable treatment history.

`Pending Review` blocks payroll for that employee. `Applicable` with a zero result remains different from `Not Applicable`.

## 7. Salary structure

Every employee included in a Payroll Entry needs an active submitted Salary Structure Assignment. Malaysia Workforce does not create a parallel salary structure or payroll run.

## 8. Availability and staffing setup

1. Create an effective-dated `Cafe Coverage Template` for each Company/location. Rows describe weekday demand, time, headcount, Designation, optional standard Skill and criticality.
2. Create a `Cafe Staffing Plan` for the 14-day cycle and use **Open Availability**.
3. Employees use **My Availability**, a standard authenticated Web Form. Copying the previous cycle always asks for confirmation.
4. Use **Generate Proposal**, resolve visible coverage gaps and use the standard Workflow action **Approve and Publish**.
5. Approval creates submitted standard `Shift Assignment` records. Review the final schedule in the HRMS roster.

For public holidays, university periods, events, promotions, closures or forecast changes, edit the generated dated coverage rows before generating the proposal and mark the changed rows as date overrides with a reason.

## 9. Holiday lists

Assign the correct state/location Holiday List to employees or shifts. Public-holiday pay relies on the applicable holiday context and must be tested for each operating state.

## EPF i-Akaun and legacy control

Use `Portal Only` to generate the current i-Akaun human-entry worksheet and retain acknowledgement evidence. `Enable Legacy EPF e-Caruman CSV (UAT Only)` remains disabled in production. Enabling it only permits isolated comparison testing; that artifact cannot be marked as an official submission.

## Kiosk and standard self-service

Register one kiosk ID and signing secret, assign only the `Malaysia Kiosk` role to its integration user, and set each employee PIN/QR through the credential-rotation API. The endpoint is signed, idempotent by event ID, records device/server timestamps, warns on offline clock drift and creates standard `Employee Checkin`. Use standard Frappe HR web/mobile for leave, claims, payslips, onboarding and employee details.

## Production activation

Install an adapter app exposing the selected bank format through the `malaysia_workforce_bank_adapters` hook. Complete bank UAT, rule review, HRD registration and restore testing, attach evidence, then call `malaysia_workforce.compliance.activation.activate_company`. Configuration changes invalidate the activation hash and require re-activation.

## Split shifts and standard Frappe HR settings

Malaysia Workforce avoids split shifts and handovers. If an evidenced manager exception requires two non-overlapping standard assignments on one date, first enable **HR Settings → Allow Multiple Shift Assignments for Same Date** and validate the employee's agreement/rest limits.
