#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-}:src:apps"
PY="${ROOT}/.venv/bin/python"
[ -x "$PY" ] || PY=python3

echo "== US-038 AI feedback unit =="
"$PY" -m pytest -q tests/unit/test_ai_feedback_validation.py

echo "== US-038 AI feedback integration =="
"$PY" -m pytest -q tests/integration/test_ai_feedback.py

if [ -d "$ROOT/frontend/node_modules" ]; then
  echo "== US-038 AI feedback e2e =="
  export LIVELEAD_DISCOVERY_USE_MOCK_CONNECTORS=false
  export LIVELEAD_DISCOVERY_COPILOT_PROVIDER=deterministic
  export LIVELEAD_EXPOSE_E2E_DISCOVERY_RSS_FIXTURE=true
  unset LIVELEAD_GOOGLE_AI_STUDIO_API_KEY 2>/dev/null || true
  if [ -f "$ROOT/frontend/.playwright-browser.env" ]; then
    # shellcheck source=/dev/null
    source "$ROOT/frontend/.playwright-browser.env"
  fi
  fuser -k 8000/tcp 4173/tcp 2>/dev/null || true
  sleep 0.5
  (cd "$ROOT/frontend" && npx playwright test e2e/ai-feedback.spec.ts)
fi

echo "== US-038 AI feedback verify complete =="