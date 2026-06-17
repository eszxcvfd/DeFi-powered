#!/usr/bin/env bash
# US-046 — Connector health surface baseline.
#
# Runs the unit + integration tests that prove the
# closed `ConnectorHealthStatus` enum, the bounded
# `ConnectorHealthComputer` operations, the
# secret-safe payload reuse from US-041, the
# bounded window bound by the `US-040`
# `EnvironmentMode`, the `MetricRegistry`
# extension from US-042, the `AlertMetric` enum
# extension from US-041, the audit entry shape,
# the RBAC contract from US-027, and the
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

echo "== US-046 prerequisite US-026 audit log =="
"$PY" -m pytest -q tests/unit/test_audit_log_model.py

echo "== US-046 prerequisite US-041 alert sanitizer =="
"$PY" -m pytest -q tests/unit/test_alert_rules.py

echo "== US-046 connector health status enum closure =="
"$PY" -m pytest -q tests/unit/test_connector_health_status_enum.py

echo "== US-046 connector health window bound =="
"$PY" -m pytest -q tests/unit/test_connector_health_window_bound.py

echo "== US-046 connector health computer =="
"$PY" -m pytest -q tests/unit/test_connector_health_computer.py

echo "== US-046 connector health audit sanitizer =="
"$PY" -m pytest -q tests/unit/test_connector_health_audit_sanitizer.py

echo "== US-046 connector health service =="
"$PY" -m pytest -q tests/unit/test_connector_health_service.py

echo "== US-046 connector health REST API + RBAC =="
"$PY" -m pytest -q tests/integration/test_connector_health_api.py

echo "== US-046 connector health security contract =="
"$PY" -m pytest -q tests/integration/test_connector_health_security.py

echo "== US-046 verify complete =="
echo
echo "Operator runbook (US-046 ops evidence):"
echo "  docs/ops/connector-health-runbook.md"
echo
echo "Update the durable story with:"
echo "  scripts/bin/harness-cli story update --id US-046 --status implemented --unit 1 --integration 1 --e2e 1 --platform 1 --verify ./scripts/verify-us-046.sh"
echo "  scripts/bin/harness-cli story verify US-046"
