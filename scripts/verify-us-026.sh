#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-}:src"
if [ -f "$ROOT/frontend/.playwright-browser.env" ]; then
  # shellcheck source=/dev/null
  source "$ROOT/frontend/.playwright-browser.env"
fi
PY="${ROOT}/.venv/bin/python"
[ -x "$PY" ] || PY=python3

./scripts/verify-us-025.sh

echo "== US-026 audit log unit =="
"$PY" -m pytest -q tests/unit/test_audit_log_model.py

echo "== US-026 audit log integration =="
"$PY" -m pytest -q tests/integration/test_audit_log_api.py

if [ -d "$ROOT/frontend/node_modules" ]; then
  echo "== US-026 audit log e2e =="
  (cd "$ROOT/frontend" && npx playwright test e2e/audit-log.spec.ts)
fi

echo "== US-026 audit log verify complete =="
