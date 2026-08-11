# Upgrade and rollback

## Before upgrade

1. Finish or freeze the current standard Payroll Entry.
2. Export unresolved attendance and submission exception lists.
3. Back up database and private/public files.
4. Record installed Frappe, ERPNext, HRMS and app commit/version.
5. Resolve duplicate accumulator/submission revisions before migration.
6. RC6 removes the release-candidate custom roster and `Malaysia Payroll Run`. The preflight migration stops before schema sync if any legacy operational records exist. Export, reconcile and remove those records deliberately; the migration never guesses how to merge them.
7. If an older RC created `Employer EPF`, `Employer SOCSO` or `Employer EIS` Salary Components, retire them through normal ERPNext administration only after proving they are unused.
8. Run the diagnostic and retain its output.

## Upgrade

```bash
cd frappe-bench
bench --site your-site backup --with-files
git -C apps/malaysia_workforce fetch --all
git -C apps/malaysia_workforce checkout <approved-tag>
./env/bin/pip install -e apps/malaysia_workforce
bench --site your-site migrate
bench build --app malaysia_workforce
bench restart
bench --site your-site execute malaysia_workforce.diagnostics.run
```

Run the staging regression matrix before production.

## Rule-table updates

A statutory table update must include:

- new effective-dated data file or calculator version;
- source URL/document metadata and SHA-256;
- official examples or independent expected results;
- automated tests;
- migration only when data model changes;
- release note and new `rules_reviewed_through` decision.

Never replace a historical table in place if submitted snapshots depend on it.

## Rollback

Application rollback is safe only if the older code understands all newer DocTypes/fields and no irreversible migration occurred. Prefer restoring the pre-upgrade database/files backup and matching app commits. Never downgrade only the Python code against a migrated production database without a rehearsed rollback plan.
