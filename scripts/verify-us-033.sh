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

echo "== US-033 prerequisite US-032 discovery unit+integration =="
"$PY" -m pytest -q \
  tests/unit/test_live_source_readiness.py \
  tests/unit/test_live_feed_connector.py \
  tests/unit/test_rss_parse.py \
  tests/unit/test_feed_filter.py \
  tests/unit/test_persist_discovery.py \
  tests/integration/test_live_feed_discovery.py \
  tests/integration/test_discovery_jobs_api.py \
  tests/integration/test_connectors_api.py

echo "== US-033 public website Playwright discovery unit =="
"$PY" -m pytest -q \
  tests/unit/test_browser_discovery_recipe.py \
  tests/unit/test_browser_source_readiness.py \
  tests/unit/test_playwright_discovery_challenge.py

echo "== US-033 public website Playwright discovery integration =="
"$PY" -m pytest -q tests/integration/test_playwright_website_discovery.py

if [ -d "$ROOT/frontend/node_modules" ]; then
  echo "== US-033 public website Playwright discovery e2e =="
  export LIVELEAD_DISCOVERY_USE_MOCK_CONNECTORS=true
  export LIVELEAD_EXPOSE_E2E_DISCOVERY_RSS_FIXTURE=true
  export LIVELEAD_EXPOSE_E2E_DISCOVERY_WEBSITE_FIXTURE=true
  if [ -f "$ROOT/frontend/.playwright-browser.env" ]; then
    # shellcheck source=/dev/null
    source "$ROOT/frontend/.playwright-browser.env"
  fi
  (cd "$ROOT/frontend" && npx playwright test e2e/website-playwright-discovery.spec.ts)
fi

echo "== US-033 public website Playwright discovery verify complete =="