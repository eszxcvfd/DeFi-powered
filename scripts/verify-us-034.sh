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

echo "== US-034 prerequisite US-033 discovery unit+integration =="
"$PY" -m pytest -q \
  tests/unit/test_browser_discovery_recipe.py \
  tests/unit/test_browser_source_readiness.py \
  tests/unit/test_playwright_discovery_challenge.py \
  tests/integration/test_playwright_website_discovery.py

echo "== US-034 Selenium alternate-adapter discovery unit =="
"$PY" -m pytest -q \
  tests/unit/test_selenium_discovery_challenge.py

echo "== US-034 Selenium alternate-adapter discovery integration =="
"$PY" -m pytest -q tests/integration/test_selenium_website_discovery.py

if [ -d "$ROOT/frontend/node_modules" ]; then
  echo "== US-034 Selenium alternate-adapter discovery e2e =="
  export LIVELEAD_DISCOVERY_USE_MOCK_CONNECTORS=true
  export LIVELEAD_EXPOSE_E2E_DISCOVERY_RSS_FIXTURE=true
  export LIVELEAD_EXPOSE_E2E_DISCOVERY_WEBSITE_FIXTURE=true
  if [ -f "$ROOT/frontend/.playwright-browser.env" ]; then
    # shellcheck source=/dev/null
    source "$ROOT/frontend/.playwright-browser.env"
  fi
  (cd "$ROOT/frontend" && npx playwright test e2e/selenium-website-discovery.spec.ts)
fi

echo "== US-034 Selenium alternate-adapter discovery verify complete =="