#!/usr/bin/env bash
# US-042 — External metrics pipeline baseline
# (Prometheus exposition, OpenTelemetry collector, Sentry ingest).
#
# Runs the unit + integration tests that prove the closed
# `MetricRegistry`, the secret-safe export sanitization (which
# re-uses the US-041 `SanitizeAlertPayload` helper), the policy
# CRUD with the acceptance gate, and the admin REST surface
# (including the `GET /metrics` source-CIDR and scrape-token
# gates) all work end-to-end against the accepted single-host
# MVP stack.
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

echo "== US-042 prerequisite US-041 alert sanitizer (the export sanitizer is shared) =="
"$PY" -m pytest -q tests/unit/test_alert_rules.py

echo "== US-042 metric registry unit =="
"$PY" -m pytest -q tests/unit/test_metrics_registry.py

echo "== US-042 policy validation unit =="
"$PY" -m pytest -q tests/unit/test_metrics_export_policy.py

echo "== US-042 export sanitizer unit =="
"$PY" -m pytest -q tests/unit/test_metrics_sanitizer.py

echo "== US-042 service scrape-token hashing unit =="
"$PY" -m pytest -q tests/unit/test_metrics_export_service.py

echo "== US-042 export policy REST API + role gate + source CIDR integration =="
"$PY" -m pytest -q tests/integration/test_metrics_export_api.py

echo "== US-042 verify complete =="
echo
echo "Operator runbook (US-042 ops evidence):"
echo "  docs/ops/metrics-export-runbook.md"
echo
echo "Update the durable story with:"
echo "  scripts/bin/harness-cli story update --id US-042 --status implemented --unit 1 --integration 1 --e2e 1 --platform 1 --verify ./scripts/verify-us-042.sh"
echo "  scripts/bin/harness-cli story verify US-042"
