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

./scripts/verify-us-018.sh

echo "== US-019 report export unit + integration =="
"$PY" -m pytest -q tests/unit/test_report_export.py tests/integration/test_report_export_api.py

if [ -d "$ROOT/frontend/node_modules" ]; then
  echo "== US-019 report export e2e =="
  (cd "$ROOT/frontend" && npx playwright test e2e/report-export.spec.ts)
fi

echo "== US-019 report export verify complete =="