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

./scripts/verify-us-017.sh

echo "== US-018 content effectiveness unit + integration =="
"$PY" -m pytest -q tests/unit/test_content_effectiveness_reporting.py tests/integration/test_content_effectiveness_reporting_api.py

if [ -d "$ROOT/frontend/node_modules" ]; then
  echo "== US-018 content effectiveness e2e =="
  (cd "$ROOT/frontend" && npx playwright test e2e/content-effectiveness.spec.ts)
fi

echo "== US-018 content effectiveness verify complete =="