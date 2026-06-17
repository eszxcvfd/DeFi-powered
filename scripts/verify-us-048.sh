#!/usr/bin/env bash
# US-048 — Connector auto-disable and policy recovery baseline.
#
# Runs the unit + integration tests that prove the
# closed `AutoDisableTrigger` enum, the closed
# `AutoDisableEventStatus` enum, the bounded
# `AutoDisableEvaluator` operations, the bounded
# `AutoDisableService` operations, the
# secret-safe payload reuse from US-041, the
# bounded window bound by the `US-040`
# `EnvironmentMode`, the audit entry shape, the
# RBAC contract from US-027, and the
# owner/admin REST surface all work end-to-end
# against the accepted single-host MVP stack.
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

echo "== US-048 prerequisite US-026 audit log =="
"$PY" -m pytest -q tests/unit/test_audit_log_model.py

echo "== US-048 prerequisite US-041 alert sanitizer =="
"$PY" -m pytest -q tests/unit/test_alert_rules.py

echo "== US-048 prerequisite US-046 connector health =="
"$PY" -m pytest -q tests/unit/test_connector_health_status_enum.py

echo "== US-048 auto-disable trigger enum closure =="
"$PY" -m pytest -q tests/unit/test_auto_disable_trigger_enum.py

echo "== US-048 auto-disable thresholds bound =="
"$PY" -m pytest -q tests/unit/test_auto_disable_thresholds.py

echo "== US-048 auto-disable evaluator =="
"$PY" -m pytest -q tests/unit/test_auto_disable_evaluator.py

echo "== US-048 auto-disable service =="
"$PY" -m pytest -q tests/unit/test_auto_disable_service.py

echo "== US-048 auto-disable REST API + RBAC =="
"$PY" -m pytest -q tests/integration/test_auto_disable_api.py

echo "== US-048 verify complete =="
echo
echo "Operator runbook (US-048 ops evidence):"
echo "  docs/ops/connector-auto-disable-runbook.md"
echo
echo "Update the durable story with:"
echo "  scripts/bin/harness-cli story update --id US-048 --status implemented --unit 1 --integration 1 --e2e 1 --platform 1 --verify ./scripts/verify-us-048.sh"
echo "  scripts/bin/harness-cli story verify US-048"
