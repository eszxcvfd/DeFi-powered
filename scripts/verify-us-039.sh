#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-}:src:apps"
PY="${ROOT}/.venv/bin/python"
[ -x "$PY" ] || PY=python3

echo "== US-039 prerequisite US-038 backend =="
"$PY" -m pytest -q tests/unit/test_ai_feedback_validation.py tests/integration/test_ai_feedback.py

echo "== US-039 scoring suggestions unit =="
"$PY" -m pytest -q tests/unit/test_scoring_suggestions.py

echo "== US-039 scoring suggestions integration =="
"$PY" -m pytest -q tests/integration/test_scoring_suggestions_api.py tests/integration/test_scoring_suggestions_audit.py

if [ -d "$ROOT/frontend/node_modules" ]; then
  if [ -f "$ROOT/frontend/.playwright-browser.env" ]; then
    # shellcheck source=/dev/null
    source "$ROOT/frontend/.playwright-browser.env"
  elif ! npx --prefix "$ROOT/frontend" playwright install --dry-run chromium 2>/dev/null | grep -q "is already installed"; then
    if [ -z "${PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH:-}" ]; then
      echo "== US-039: installing Playwright chromium (or set PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH) =="
      (cd "$ROOT/frontend" && npx playwright install chromium) || true
    fi
  fi
  echo "== US-039 scoring suggestions e2e =="
  export LIVELEAD_DISCOVERY_USE_MOCK_CONNECTORS=false
  export LIVELEAD_EXPOSE_E2E_DISCOVERY_RSS_FIXTURE=true
  export LIVELEAD_DISCOVERY_COPILOT_PROVIDER=deterministic
  fuser -k 8000/tcp 4173/tcp 2>/dev/null || true
  sleep 0.5
  (cd "$ROOT/frontend" && npx playwright test e2e/scoring-suggestion.spec.ts)
fi

echo "== US-039 scoring suggestions verify complete =="