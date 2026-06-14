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

./scripts/verify-us-015.sh

echo "== US-016 funnel reporting unit + integration =="
"$PY" -m pytest -q tests/unit/test_funnel_reporting.py tests/integration/test_funnel_reporting_api.py

if [ -d "$ROOT/frontend/node_modules" ]; then
  echo "== US-016 funnel report e2e =="
  (cd "$ROOT/frontend" && npx playwright test e2e/funnel-report.spec.ts)
fi

echo "== US-016 funnel reporting verify complete =="