# Statutory scope and limitations

## Responsibility

The employer remains responsible for employee classification, wage-component treatment, current rates, filing deadlines, portal acceptance, payment and record retention. This software implements a controlled calculation and audit workflow; it does not provide legal or tax advice.

## Embedded rule versions

The release contains source-derived tables and engine identifiers for:

- EPF Third Schedule effective in 2025;
- SOCSO/LINDUNG 24 Jam schedule represented in the bundled 2026 table;
- EIS schedule represented in the bundled 2024 table;
- LHDN computerised PCB method represented by engine version `MW-STATUTORY-2026.1`;
- PERKESO combined fixed-width layout represented by the 2026 exporter.

Source PDF hashes and generated table hashes are recorded in `malaysia_workforce/statutory/data/source_manifest.json`. The original source PDFs are not redistributed in the app.

## Rule expiry control

`strict_rule_review` and `rules_reviewed_through` prevent payroll after the configured review date. Do not extend the date without checking current official publications, test examples, thresholds, contribution tables and file specifications.

## Employee-specific treatment

The app lets authorised users set each scheme to `Not Applicable` without approval, as requested. This is an operational control, not a legal exemption. A manual exclusion is stored with an effective date, actor, reason and history. Submitted records are never rewritten.

## Forms

The app provides data-capture and preparation records for TP1, TP3, employee notifications and annual statements. They are not represented as pixel-identical government-issued forms. Confirm current official forms and electronic channels before use.

## Electronic filing

Validated files and portal links are included. Direct API submission is intentionally not simulated. Browser scraping, stored portal passwords and OTP automation are not included. An API connector may only be enabled against an official, authorised interface.

## Required acceptance testing

Before first production filing, upload non-production or authorised test files to each relevant authority channel and obtain written/internal acceptance evidence. Re-test whenever an authority changes a schema, portal or contribution schedule.

## EPF exporter status

The bundled six-column EPF CSV is a legacy e-Caruman compatibility serializer, not a representation of a verified current i-Akaun (Employer) upload contract. It is disabled by default and blocked from official-submission status. Obtain portal/UAT evidence and implement a current approved adapter before production activation.
