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

./scripts/verify-us-024.sh

echo "== US-025 CloakBrowser policy unit + integration =="
"$PY" -m pytest -q tests/unit/test_cloakbrowser_policy.py tests/integration/test_cloakbrowser_policy_api.py

if [ -d "$ROOT/frontend/node_modules" ]; then
  echo "== US-025 CloakBrowser policy e2e =="
  (cd "$ROOT/frontend" && npx playwright test e2e/cloakbrowser-policy.spec.ts)
fi

echo "== US-025 CloakBrowser policy verify complete =="