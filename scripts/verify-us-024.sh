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

./scripts/verify-us-023.sh

echo "== US-024 browser profile lifecycle unit + integration =="
"$PY" -m pytest -q tests/unit/test_browser_profile_lifecycle.py tests/integration/test_browser_profiles_api.py

if [ -d "$ROOT/frontend/node_modules" ]; then
  echo "== US-024 browser profile lifecycle e2e =="
  (cd "$ROOT/frontend" && npx playwright test e2e/browser-profile-lifecycle.spec.ts)
fi

echo "== US-024 browser profile lifecycle verify complete =="