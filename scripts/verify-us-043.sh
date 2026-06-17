#!/usr/bin/env bash
# US-043 — Backup and restore operations baseline.
#
# Runs the unit + integration tests that prove the
# retention policy validation, the data-deletion
# service, the bounded restore and retention prune
# paths, and the admin REST surface (including the
# role gate, the audit-floor enforcement, the
# acceptance gate, and the data-deletion contract)
# all work end-to-end against the accepted
# single-host MVP stack.
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

echo "== US-043 prerequisite US-026 audit (sanitization shared with restore payloads) =="
"$PY" -m pytest -q tests/unit/test_audit_log_model.py

echo "== US-043 prerequisite US-040 backup (restore consumes BackupSnapshot) =="
"$PY" -m pytest -q tests/unit/test_runtime_backup.py

echo "== US-043 prerequisite US-041 sanitizer (restore payloads share the helper) =="
"$PY" -m pytest -q tests/unit/test_alert_rules.py

echo "== US-043 retention policy + data-deletion validation unit =="
"$PY" -m pytest -q tests/unit/test_backup_restore_policy.py

echo "== US-043 data-deletion service unit =="
"$PY" -m pytest -q tests/unit/test_data_deletion_service.py

echo "== US-043 backup restore REST API + role gate + acceptance gate integration =="
"$PY" -m pytest -q tests/integration/test_backup_restore_api.py

echo "== US-043 verify complete =="
echo
echo "Operator runbook (US-043 ops evidence):"
echo "  docs/ops/backup-restore-runbook.md"
echo
echo "Update the durable story with:"
echo "  scripts/bin/harness-cli story update --id US-043 --status implemented --unit 1 --integration 1 --e2e 1 --platform 1 --verify ./scripts/verify-us-043.sh"
echo "  scripts/bin/harness-cli story verify US-043"
