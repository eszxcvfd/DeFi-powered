#!/usr/bin/env bash
# Chains through verify-us-013 → … → verify-foundation.
# Harness `story verify US-014` runs this command when platform/e2e flags are set.
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

./scripts/verify-us-013.sh

echo "== US-014 dashboard overview unit + integration =="
"$PY" -m pytest -q tests/unit/test_dashboard_overview.py tests/integration/test_dashboard_overview_api.py

if [ -d "$ROOT/frontend/node_modules" ]; then
  echo "== US-014 dashboard overview e2e =="
  (cd "$ROOT/frontend" && npx playwright test e2e/dashboard-overview.spec.ts)
fi

echo "== US-014 dashboard overview verify complete =="