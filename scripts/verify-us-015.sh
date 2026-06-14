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

./scripts/verify-us-014.sh

echo "== US-015 lead outcomes unit + integration =="
"$PY" -m pytest -q tests/unit/test_lead_outcomes.py tests/integration/test_lead_outcomes_api.py

if [ -d "$ROOT/frontend/node_modules" ]; then
  echo "== US-015 lead outcomes e2e =="
  (cd "$ROOT/frontend" && npx playwright test e2e/lead-outcomes.spec.ts)
fi

echo "== US-015 lead outcomes verify complete =="