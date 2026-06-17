#!/usr/bin/env bash
# US-049 — Governed Webhook Delivery Baseline.
#
# Runs the unit + integration tests that prove the
# closed `WebhookEventType` enum, the closed
# `WebhookDeliveryStatus` enum, the bounded
# `WebhookSigner` HMAC-SHA256 operations, the
# bounded `WebhookRetryPolicy` operations, the
# bounded `WebhookDispatcher` operations, the
# bounded target URL validation, the
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

echo "== US-049 prerequisite US-026 audit log =="
"$PY" -m pytest -q tests/unit/test_audit_log_model.py

echo "== US-049 prerequisite US-041 alert sanitizer =="
"$PY" -m pytest -q tests/unit/test_alert_rules.py

echo "== US-049 prerequisite US-048 auto-disable =="
"$PY" -m pytest -q tests/unit/test_auto_disable_trigger_enum.py

echo "== US-049 webhook event type enum closure =="
"$PY" -m pytest -q tests/unit/test_webhook_event_type_enum.py

echo "== US-049 webhook thresholds bound =="
"$PY" -m pytest -q tests/unit/test_webhook_thresholds.py

echo "== US-049 webhook signer =="
"$PY" -m pytest -q tests/unit/test_webhook_signer.py

echo "== US-049 webhook retry policy =="
"$PY" -m pytest -q tests/unit/test_webhook_retry_policy.py

echo "== US-049 webhook target URL validation =="
"$PY" -m pytest -q tests/unit/test_webhook_target_url_validation.py

echo "== US-049 webhook delivery service =="
"$PY" -m pytest -q tests/unit/test_webhook_delivery_service.py

echo "== US-049 webhook REST API + RBAC =="
"$PY" -m pytest -q tests/integration/test_webhook_api.py

echo "== US-049 verify complete =="
echo
echo "Operator runbook (US-049 ops evidence):"
echo "  docs/ops/webhook-delivery-runbook.md"
echo
echo "Update the durable story with:"
echo "  scripts/bin/harness-cli story update --id US-049 --status implemented --unit 1 --integration 1 --e2e 1 --platform 1 --verify ./scripts/verify-us-049.sh"
echo "  scripts/bin/harness-cli story verify US-049"
