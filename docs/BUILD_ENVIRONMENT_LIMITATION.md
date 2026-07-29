# ERPNext live-test environment report — Malaysia Workforce RC3

**Date:** 29 July 2026  
**Requested:** Start ERPNext and test the Malaysia Workforce app fully.

## Result

ERPNext could not be started in this sandbox. This result is **not** a live-test pass.

## Resources available

- Debian 13 container
- 5 CPU cores
- Approximately 5.9 GiB RAM
- Approximately 39 GiB free disk
- Python 3.13.5
- Node 22.16.0
- Git, Chromium, Nginx and Supervisor

## Required runtime components that were absent

- Frappe Framework source
- ERPNext source
- Frappe HR source
- Bench CLI
- MariaDB/MySQL server
- Redis server
- Docker or Podman
- Python 3.14 runtime
- Node 24 runtime

## Retrieval attempts

- The configured internal Debian APT endpoints returned HTTP 404 for `trixie`, `trixie-updates` and `trixie-security` Release metadata.
- External DNS/source downloads were blocked by the sandbox network policy.
- Internal Python, npm and Go package endpoints did not provide the missing Frappe/runtime distributions.
- No pre-existing Bench, database server or remote test host was available.

## Tests completed

The RC3 source was tested without Frappe using its pure/static suite and release checks. See the RC3 test-results file and `docs/LIVE_ERPNext_TEST.md` in the package.

## Production decision

**Not approved for production.** A real disposable/staging Frappe v16 bench must execute the included `scripts/run_live_bench_test.sh`, followed by the complete business and authority UAT matrix.
