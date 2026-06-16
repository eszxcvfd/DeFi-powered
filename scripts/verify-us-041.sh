#!/usr/bin/env bash
# US-041 — Operational observability and alerting baseline.
#
# Runs the unit + integration tests that prove the alert rule
# grammar, the secret-safe payload sanitizer, the signal providers,
# the evaluator, and the admin REST surface all work end-to-end
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

echo "== US-041 prerequisite US-026 audit (sanitization shared with alert payloads) =="
"$PY" -m pytest -q tests/unit/test_audit_log_model.py

echo "== US-041 prerequisite US-040 runtime (operator summary depends on readiness) =="
"$PY" -m pytest -q tests/unit/test_runtime_launch_gate.py

echo "== US-041 alert rule validation + sanitizer + dedup unit =="
"$PY" -m pytest -q tests/unit/test_alert_rules.py

echo "== US-041 signal providers unit =="
"$PY" -m pytest -q tests/unit/test_alert_evaluator_signals.py

echo "== US-041 alert REST API + role gate integration =="
"$PY" -m pytest -q tests/integration/test_observability_api.py

echo "== US-041 alert evaluator integration =="
"$PY" -m pytest -q tests/integration/test_alert_evaluator.py

if [ -d "$ROOT/frontend/node_modules" ]; then
  echo "== US-041 observability panel e2e =="
  (cd "$ROOT/frontend" && npx playwright test e2e/observability.spec.ts)
fi

echo "== US-041 verify complete =="
echo
echo "Operator runbook (US-041 ops evidence):"
echo "  docs/ops/observability-runbook.md"
echo
echo "Update the durable story with:"
echo "  scripts/bin/harness-cli story update --id US-041 --status implemented --unit 1 --integration 1 --e2e 1 --platform 1 --verify ./scripts/verify-us-041.sh"
echo "  scripts/bin/harness-cli story verify US-041"
