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

./scripts/verify-us-020.sh

echo "== US-021 read-only browser actions unit + integration =="
"$PY" -m pytest -q tests/unit/test_browser_action_policy.py tests/integration/test_browser_session_actions_api.py

if [ -d "$ROOT/frontend/node_modules" ]; then
  echo "== US-021 browser read-only actions e2e =="
  (cd "$ROOT/frontend" && npx playwright test e2e/browser-read-only-actions.spec.ts)
fi

echo "== US-021 read-only browser actions verify complete =="