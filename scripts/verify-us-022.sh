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

./scripts/verify-us-021.sh

echo "== US-022 confirmation-gated browser actions unit + integration =="
"$PY" -m pytest -q tests/unit/test_browser_action_confirmation.py tests/integration/test_browser_action_confirmation_api.py

if [ -d "$ROOT/frontend/node_modules" ]; then
  echo "== US-022 browser confirmation e2e =="
  (cd "$ROOT/frontend" && npx playwright test e2e/browser-confirmation-actions.spec.ts)
fi

echo "== US-022 confirmation-gated browser actions verify complete =="