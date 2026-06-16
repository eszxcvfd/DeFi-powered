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

echo "== US-030 event watchlist unit =="
"$PY" -m pytest -q \
  tests/unit/test_event_watchlist_models.py \
  tests/unit/test_event_watchlist_service.py

echo "== US-030 event watchlist integration =="
"$PY" -m pytest -q \
  tests/integration/test_event_watchlist_api.py

if [ -d "$ROOT/frontend/node_modules" ]; then
  echo "== US-030 event watchlist e2e =="
  (cd "$ROOT/frontend" && npx playwright test e2e/event-watchlist.spec.ts)
fi

echo "== US-030 event watchlist verify complete =="
