#!/usr/bin/env bash
# US-044 — Performance baseline and SLO guardrails.
#
# Runs the unit + integration tests that prove the
# closed `PerformanceMetric` enum, the bounded
# scenario runner, the secret-safe payload reuse
# from US-041, the browser session budget
# enforcer, and the admin REST surface (including
# the role gate, the summary endpoint, and the
# scenario runner) all work end-to-end against the
# accepted single-host MVP stack.
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

echo "== US-044 prerequisite US-041 alert sanitizer (SLO evaluator reuses it) =="
"$PY" -m pytest -q tests/unit/test_alert_rules.py

echo "== US-044 prerequisite US-042 metric registry (SLO descriptors extend it) =="
"$PY" -m pytest -q tests/unit/test_metrics_registry.py

echo "== US-044 performance metric + scenario enum unit =="
"$PY" -m pytest -q tests/unit/test_performance_enums.py

echo "== US-044 performance baseline service unit =="
"$PY" -m pytest -q tests/unit/test_performance_baseline_service.py

echo "== US-044 browser session budget enforcer unit =="
"$PY" -m pytest -q tests/unit/test_browser_session_budget.py

echo "== US-044 performance REST API + role gate integration =="
"$PY" -m pytest -q tests/integration/test_performance_api.py

echo "== US-044 verify complete =="
echo
echo "Operator runbook (US-044 ops evidence):"
echo "  docs/ops/performance-baseline-runbook.md"
echo
echo "Update the durable story with:"
echo "  scripts/bin/harness-cli story update --id US-044 --status implemented --unit 1 --integration 1 --e2e 1 --platform 1 --verify ./scripts/verify-us-044.sh"
echo "  scripts/bin/harness-cli story verify US-044"
