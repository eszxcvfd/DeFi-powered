#!/usr/bin/env bash
# US-045 — Event calendar export (ICS) baseline.
#
# Runs the unit + integration tests that prove the
# closed `CalendarScope` enum, the bounded
# `CalendarExportService` operations, the secret-
# safe payload reuse from US-041, the calendar
# `STATUS` mapping, the export token TTL bound
# from the `US-040` `EnvironmentMode`, the
# tokenized ICS endpoint, the audit entry shape,
# the RBAC contract from `US-027`, and the
# admin/current-user REST surface all work end-to-
# end against the accepted single-host MVP stack.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-}:src:."
if [ -f "$ROOT/frontend/.playwright-browser.env" ]; then
  # shellcheck source=/dev/null
  source "$ROOT/frontend/.playwright-browser.env"
fi
PY="${ROOT}/.venv/bin/python"
[ -x "$PY" ] || PY=python3

echo "== US-045 prerequisite US-026 audit log =="
"$PY" -m pytest -q tests/unit/test_audit_log_model.py

echo "== US-045 calendar scope enum closure =="
"$PY" -m pytest -q tests/unit/test_calendar_scope_enum.py

echo "== US-045 calendar export formatter =="
"$PY" -m pytest -q tests/unit/test_calendar_export_formatter.py

echo "== US-045 calendar export token TTL bound =="
"$PY" -m pytest -q tests/unit/test_calendar_export_token_ttl.py

echo "== US-045 calendar export audit sanitizer =="
"$PY" -m pytest -q tests/unit/test_calendar_audit_sanitizer.py

echo "== US-045 calendar export service =="
"$PY" -m pytest -q tests/unit/test_calendar_export_service.py

echo "== US-045 calendar export REST API + RBAC =="
"$PY" -m pytest -q tests/integration/test_calendar_export_api.py

echo "== US-045 calendar export security contract =="
"$PY" -m pytest -q tests/integration/test_calendar_export_security.py

echo "== US-045 verify complete =="
echo
echo "Operator runbook (US-045 ops evidence):"
echo "  docs/ops/calendar-export-runbook.md"
echo
echo "Update the durable story with:"
echo "  scripts/bin/harness-cli story update --id US-045 --status implemented --unit 1 --integration 1 --e2e 1 --platform 1 --verify ./scripts/verify-us-045.sh"
echo "  scripts/bin/harness-cli story verify US-045"
