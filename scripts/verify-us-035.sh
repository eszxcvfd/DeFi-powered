#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-}:src:apps"
PY="${ROOT}/.venv/bin/python"
[ -x "$PY" ] || PY=python3

echo "== US-035 discovery schedule unit =="
"$PY" -m pytest -q tests/unit/test_discovery_schedule_recurrence.py

echo "== US-035 discovery schedule integration =="
"$PY" -m pytest -q tests/integration/test_discovery_schedules.py

echo "== US-035 scheduler process once =="
"$PY" -m apps.scheduler.main

if [ -d "$ROOT/frontend/node_modules" ]; then
  echo "== US-035 discovery schedule e2e =="
  export LIVELEAD_DISCOVERY_USE_MOCK_CONNECTORS=true
  if [ -f "$ROOT/frontend/.playwright-browser.env" ]; then
    # shellcheck source=/dev/null
    source "$ROOT/frontend/.playwright-browser.env"
  fi
  fuser -k 8000/tcp 4173/tcp 2>/dev/null || true
  sleep 0.5
  (cd "$ROOT/frontend" && npx playwright test e2e/discovery-schedule.spec.ts)
fi

echo "== US-035 scheduled discovery verify complete =="