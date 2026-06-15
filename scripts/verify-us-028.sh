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

echo "== US-028 member management unit =="
"$PY" -m pytest -q \
  tests/unit/test_member_management_policy.py

echo "== US-028 member management integration =="
"$PY" -m pytest -q \
  tests/integration/test_member_management_api.py

if [ -d "$ROOT/frontend/node_modules" ]; then
  echo "== US-028 member management e2e =="
  (cd "$ROOT/frontend" && npx playwright test e2e/member-management.spec.ts)
fi

echo "== US-028 member management verify complete =="
