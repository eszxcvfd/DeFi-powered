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

echo "== US-031 event overrides unit =="
"$PY" -m pytest -q \
  tests/unit/test_event_overrides_models.py \
  tests/unit/test_event_overrides_service.py

echo "== US-031 event overrides integration =="
"$PY" -m pytest -q \
  tests/integration/test_event_overrides_api.py

if [ -d "$ROOT/frontend/node_modules" ]; then
  echo "== US-031 event overrides e2e =="
  (cd "$ROOT/frontend" && npx playwright test e2e/event-overrides.spec.ts)
fi

echo "== US-031 event overrides verify complete =="
