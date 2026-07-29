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
- Default Payroll Payable Account in Frappe HR

Use separate companies for separate legal employers. Do not reuse one statutory employer number across unrelated Company records.

## 2. Malaysia Workforce Settings

Review every field before production:

### Roster and attendance

- Slot length, minimum shift duration and minimum hourly rate.
- Minimum-wage effective date.
- Application reminders.
- Check-in windows and automatic verification tolerance.
- Whether mobile geolocation is required.
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

There is no approval step. An authorised HR/payroll user saves changes immediately. Use permissions to limit this power. Enter a reason and review the warning before setting `Not Applicable` for a person recorded under a contract of service.

`Pending Review` blocks payroll for that employee. `Applicable` with a zero result remains different from `Not Applicable`.

## 7. Salary structure

Every employee included in a Payroll Entry needs an active submitted Salary Structure Assignment. The app can create a minimal flexible-worker structure for casual pay, but production accounts and component policies must still be reviewed.

## 8. Roster setup

Create a Casual Roster with:

- date range and application window;
- manager, branch, location, project and instructions;
- one or more coverage rows with date, start/end, role, headcount and rate.

Open the roster. Employees see it only when eligible. They submit exact windows and choose whether exact selected hours require confirmation.

## 9. Holiday lists

Assign the correct state/location Holiday List to employees or shifts. Public-holiday pay relies on the applicable holiday context and must be tested for each operating state.

## EPF legacy CSV control

`Enable Legacy EPF e-Caruman CSV (UAT Only)` is disabled by default. Leave it disabled in production. The serializer follows the discontinued e-Caruman guide and is not a verified current i-Akaun (Employer) adapter. Enabling it only permits isolated comparison/UAT generation; the resulting file remains `Generated`, never `Ready for Portal`, and cannot be marked as an official submission.

## Split shifts and standard Frappe HR settings

Malaysia Workforce creates standard Frappe HR Shift Assignment records. To allow two non-overlapping assignments for one employee on the same date, enable **HR Settings → Allow Multiple Shift Assignments for Same Date**. When this standard setting is disabled, the employee portal disables split-shift opt-in and server validation blocks a second same-date selection before roster publication.
