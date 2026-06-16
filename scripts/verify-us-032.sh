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

./scripts/verify-us-031.sh

echo "== US-032 live feed discovery unit =="
"$PY" -m pytest -q \
  tests/unit/test_live_source_readiness.py \
  tests/unit/test_live_feed_connector.py \
  tests/unit/test_rss_parse.py \
  tests/unit/test_feed_filter.py \
  tests/unit/test_persist_discovery.py

echo "== US-032 live feed discovery integration =="
"$PY" -m pytest -q \
  tests/integration/test_live_feed_discovery.py \
  tests/integration/test_discovery_jobs_api.py \
  tests/integration/test_connectors_api.py

if [ -d "$ROOT/frontend/node_modules" ]; then
  echo "== US-032 live feed discovery e2e =="
  export LIVELEAD_DISCOVERY_USE_MOCK_CONNECTORS=false
  (cd "$ROOT/frontend" && npx playwright test e2e/live-feed-discovery.spec.ts)
fi

echo "== US-032 live feed API discovery verify complete =="