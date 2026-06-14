#!/usr/bin/env bash
# Chains through verify-us-012 → … → verify-foundation (ruff, full pytest, Playwright e2e, smokes).
# Harness `story verify US-013` runs this command when platform/e2e flags are set.
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

./scripts/verify-us-012.sh

echo "== US-013 follow-up reminders unit + integration =="
"$PY" -m pytest -q tests/unit/test_follow_up_reminders.py tests/integration/test_follow_up_reminders_api.py

echo "== US-013 follow-up reminders verify complete =="