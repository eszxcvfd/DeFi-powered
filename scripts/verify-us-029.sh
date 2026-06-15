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

echo "== US-029 notification delivery unit =="
"$PY" -m pytest -q \
  tests/unit/test_notifications_policy.py

echo "== US-029 notification delivery integration =="
"$PY" -m pytest -q \
  tests/integration/test_notifications_api.py

if [ -d "$ROOT/frontend/node_modules" ]; then
  echo "== US-029 notification delivery e2e =="
  (cd "$ROOT/frontend" && npx playwright test e2e/notifications.spec.ts)
fi

echo "== US-029 notification delivery verify complete =="
