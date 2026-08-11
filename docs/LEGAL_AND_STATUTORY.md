# Statutory scope and limitations

## Responsibility

The employer remains responsible for employee classification, wage-component treatment, current rates, filing deadlines, portal acceptance, payment and record retention. This software implements a controlled calculation and audit workflow; it does not provide legal or tax advice.

## Embedded rule versions

The release contains source-derived tables and engine identifiers for:

- EPF Third Schedule effective in 2025;
- SOCSO/LINDUNG 24 Jam schedule represented in the bundled 2026 table;
- EIS schedule represented in the bundled 2024 table;
- LHDN computerised PCB method represented by engine version `MW-STATUTORY-2026.1`;
- TP1 2026 controlled relief catalogue and caps;
- 2025 effective-dated minimum wage and Part-Time Employees Regulations pay bands;
- HRD Corp employer levy represented by `HRDCORP-LEVY-2026-01`;
- PERKESO combined fixed-width layout represented by the 2026 exporter.

Source PDF hashes and generated table hashes are recorded in `malaysia_workforce/statutory/data/source_manifest.json`. The original source PDFs are not redistributed in the app.

## Rule expiry control

Global and Company rule-review deadlines prevent payroll after the reviewed date. Scheduled ToDos warn before expiry. Do not extend either date without checking current official publications, examples, thresholds, contribution tables and file specifications.

## Employee-specific treatment

The app permits `Not Applicable` only with HR Manager/System Manager authority, a controlled reason, detailed notes and attached evidence. This is an operational control, not a legal exemption. Submitted records are never rewritten.

## Forms

The app provides data-capture and preparation records for TP1, TP3, employee notifications and annual statements. They are not represented as pixel-identical government-issued forms. Confirm current official forms and electronic channels before use.

## Electronic filing

Validated files and portal links are included. Direct API submission is intentionally not simulated. Browser scraping, stored portal passwords and OTP automation are not included. An API connector may only be enabled against an official, authorised interface.

## Required acceptance testing

Before first production filing, upload non-production or authorised test files to each relevant authority channel and obtain written/internal acceptance evidence. Re-test whenever an authority changes a schema, portal or contribution schedule.

## EPF exporter status

The normal EPF handoff is a current i-Akaun (Employer) portal preparation worksheet with human acknowledgement evidence; it is not presented as an upload schema. The six-column e-Caruman compatibility serializer is disabled, UAT-only and blocked from official-submission status.
