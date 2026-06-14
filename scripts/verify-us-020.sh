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

./scripts/smoke-browser-worker.sh

if [ "${LIVELEAD_BROWSER_LIVE_TEST:-}" = "1" ]; then
  echo "== US-020 live Playwright integration (optional) =="
  LIVELEAD_BROWSER_AUTOMATION_MODE=playwright "$PY" -m pytest -q tests/integration/test_browser_sessions_playwright_live.py
fi

echo "== US-020 browser session unit + integration =="
"$PY" -m pytest -q tests/unit/test_browser_session_lifecycle.py tests/integration/test_browser_sessions_api.py

if [ -d "$ROOT/frontend/node_modules" ]; then
  echo "== US-020 browser session e2e =="
  (cd "$ROOT/frontend" && npx playwright test e2e/browser-session.spec.ts)
fi

echo "== US-020 browser session verify complete =="