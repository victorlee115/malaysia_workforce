#!/usr/bin/env bash
set -Eeuo pipefail

BENCH_DIR="${BENCH_DIR:-$PWD}"
SITE="${SITE:-test_malaysia_workforce.localhost}"
APP_SOURCE="${APP_SOURCE:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
CREATE_SITE="${CREATE_SITE:-1}"
RUN_HTTP_SMOKE="${RUN_HTTP_SMOKE:-1}"
KEEP_SITE="${KEEP_SITE:-1}"
LOG_DIR="${LOG_DIR:-$BENCH_DIR/logs/malaysia-workforce-live-test}"
DB_ROOT_PASSWORD="${DB_ROOT_PASSWORD:-}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"
COMPANY="${COMPANY:-}"
MARIADB_CLIENT_LIB="${MARIADB_CLIENT_LIB:-}"

if [ -n "$MARIADB_CLIENT_LIB" ]; then
    export DYLD_LIBRARY_PATH="$MARIADB_CLIENT_LIB${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"
fi

mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/${SITE//\//_}-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$LOG_FILE") 2>&1

fail() { echo "ERROR: $*" >&2; exit 1; }
step() { echo; echo "===== $* ====="; }

command -v bench >/dev/null || fail "bench is not installed or not on PATH"
command -v node >/dev/null || fail "node is unavailable"
command -v curl >/dev/null || fail "curl is unavailable"
[ -d "$APP_SOURCE" ] || fail "APP_SOURCE is not a directory: $APP_SOURCE"
[ -d "$BENCH_DIR/apps/frappe" ] || fail "Frappe source is missing from $BENCH_DIR/apps/frappe"
[ -d "$BENCH_DIR/apps/erpnext" ] || fail "ERPNext source is missing from $BENCH_DIR/apps/erpnext"
[ -d "$BENCH_DIR/apps/hrms" ] || fail "Frappe HR source is missing from $BENCH_DIR/apps/hrms"
[ -x "$BENCH_DIR/env/bin/python" ] || fail "Bench virtual-environment Python is missing"
cd "$BENCH_DIR"

./env/bin/python - <<'PY'
import sys
if sys.version_info < (3, 14) or sys.version_info >= (3, 15):
    raise SystemExit(f"Bench Python 3.14.x required; found {sys.version.split()[0]}")
PY
node -e 'const [m]=process.versions.node.split(".").map(Number); if(m<24){console.error(`Node >=24 required; found ${process.versions.node}`); process.exit(1)}'

assert_app_commit() {
    local app="$1"
    local expected="$2"
    local actual
    actual="$(git -C "$BENCH_DIR/apps/$app" rev-parse --short=7 HEAD)"
    [ "$actual" = "$expected" ] || fail "$app is at $actual; compatibility-lock.json requires $expected"
}
assert_app_commit frappe 6a329d0
assert_app_commit erpnext 22247ab
assert_app_commit hrms f281e8b

step "Install/update Malaysia Workforce app source"
if [ ! -d apps/malaysia_workforce ]; then
    bench get-app "$APP_SOURCE"
else
    expected_version="$(sed -n 's/^__version__ = "\([^"]*\)"/\1/p' "$APP_SOURCE/malaysia_workforce/__init__.py")"
    installed_version="$(sed -n 's/^__version__ = "\([^"]*\)"/\1/p' apps/malaysia_workforce/malaysia_workforce/__init__.py)"
    [ -n "$expected_version" ] || fail "Cannot determine Malaysia Workforce version from APP_SOURCE"
    [ "$installed_version" = "$expected_version" ] || fail \
        "apps/malaysia_workforce is version ${installed_version:-unknown}; expected $expected_version. Replace it with APP_SOURCE before testing."
    ./env/bin/python -m pip install -e apps/malaysia_workforce
fi

if [ ! -f "sites/$SITE/site_config.json" ]; then
    [ "$CREATE_SITE" = "1" ] || fail "Site $SITE does not exist and CREATE_SITE is disabled"
    [ -n "$DB_ROOT_PASSWORD" ] || fail "DB_ROOT_PASSWORD is required to create a disposable site"
    step "Create disposable Frappe site"
    bench new-site "$SITE" \
        --db-type mariadb \
        --db-root-password "$DB_ROOT_PASSWORD" \
        --admin-password "$ADMIN_PASSWORD" \
        --no-mariadb-socket
fi

installed_apps() {
    # Normalise both one-column output and app/version tables.
    bench --site "$SITE" list-apps 2>/dev/null | awk 'NF {print $1}'
}
install_if_missing() {
    local app="$1"
    if ! installed_apps | grep -qx "$app"; then
        bench --site "$SITE" install-app "$app"
    fi
}

step "Install ERPNext, Frappe HR and Malaysia Workforce"
install_if_missing erpnext
install_if_missing hrms
install_if_missing malaysia_workforce
bench --site "$SITE" set-config allow_tests true

step "Run migration twice to test idempotency"
bench --site "$SITE" migrate
bench --site "$SITE" migrate

step "Build application assets"
bench build --app malaysia_workforce

step "Run pure/static app test suite using the Bench virtual environment"
./env/bin/python -m pytest -q apps/malaysia_workforce/malaysia_workforce/tests

step "Run live Frappe payroll and permission scenarios"
bench --site "$SITE" execute malaysia_workforce.live_tests.scenarios.run_statutory_profile
bench --site "$SITE" execute malaysia_workforce.live_tests.scenarios.run_all
bench --site "$SITE" execute malaysia_workforce.live_tests.scenarios.run_source_tamper
bench --site "$SITE" execute malaysia_workforce.live_tests.scenarios.run_lindung_release
bench --site "$SITE" execute malaysia_workforce.live_tests.scenarios.run_report_permission_isolation
bench --site "$SITE" execute malaysia_workforce.live_tests.scenarios.run_overtime_monthly_limit
bench --site "$SITE" execute malaysia_workforce.live_tests.scenarios.run_review_guardrails
bench --site "$SITE" execute malaysia_workforce.live_tests.scenarios.run_tax_self_service

if [ -n "$COMPANY" ]; then
	step "Assert configured Malaysia company readiness"
    bench --site "$SITE" execute malaysia_workforce.diagnostics.assert_ready \
        --kwargs "{\"company\": \"$COMPANY\"}"
fi

step "Bench health"
bench --site "$SITE" doctor

SERVER_PID=""
cleanup_server() {
    if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
        kill -- -"$SERVER_PID" 2>/dev/null || kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
}
trap cleanup_server EXIT

if [ "$RUN_HTTP_SMOKE" = "1" ]; then
    step "Start development processes and perform HTTP health check"
    setsid bench start >"$LOG_DIR/bench-start-${SITE//\//_}.log" 2>&1 &
    SERVER_PID=$!
    healthy=0
    for _ in $(seq 1 90); do
        if curl -fsS -H "Host: $SITE" http://127.0.0.1:8000/api/method/ping | grep -q 'pong'; then
            healthy=1
            break
        fi
        sleep 2
    done
    [ "$healthy" = "1" ] || fail "ERPNext HTTP health check failed; inspect $LOG_DIR/bench-start-${SITE//\//_}.log"
    curl -fsS -H "Host: $SITE" http://127.0.0.1:8000/api/method/ping
    cleanup_server
    SERVER_PID=""
fi

step "Result"
echo "LIVE BENCH RUNTIME SMOKE PASSED"
echo "Site: $SITE"
if [ -n "$COMPANY" ]; then
    echo "Configured company readiness: PASSED ($COMPANY)"
else
    echo "Configured company readiness: NOT ASSESSED (set COMPANY to require it)"
fi
echo "Log: $LOG_FILE"

if [ "$KEEP_SITE" != "1" ]; then
    [ -n "$DB_ROOT_PASSWORD" ] || fail "DB_ROOT_PASSWORD is required to drop the test site"
    bench drop-site "$SITE" --force --db-root-password "$DB_ROOT_PASSWORD" --no-backup
fi
