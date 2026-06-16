#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-}:src:apps"
PY="${ROOT}/.venv/bin/python"
[ -x "$PY" ] || PY=python3

echo "== US-037 discovery copilot unit =="
"$PY" -m pytest -q tests/unit/test_discovery_copilot_schema.py

echo "== US-037 discovery copilot integration =="
"$PY" -m pytest -q tests/integration/test_discovery_copilot.py

if [ -d "$ROOT/frontend/node_modules" ]; then
  echo "== US-037 discovery copilot e2e =="
  export LIVELEAD_DISCOVERY_USE_MOCK_CONNECTORS=true
  if [ -f "$ROOT/frontend/.playwright-browser.env" ]; then
    # shellcheck source=/dev/null
    source "$ROOT/frontend/.playwright-browser.env"
  fi
  fuser -k 8000/tcp 4173/tcp 2>/dev/null || true
  sleep 0.5
  (cd "$ROOT/frontend" && npx playwright test e2e/discovery-copilot.spec.ts)
fi

echo "== US-037 discovery copilot verify complete =="