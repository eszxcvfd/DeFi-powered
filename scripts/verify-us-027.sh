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

./scripts/verify-us-026.sh

echo "== US-027 identity access unit =="
"$PY" -m pytest -q \
  tests/unit/test_passwords.py \
  tests/unit/test_roles.py \
  tests/unit/test_sessions_and_rate_limit.py

echo "== US-027 identity access integration =="
"$PY" -m pytest -q \
  tests/integration/test_auth_api.py \
  tests/integration/test_auth_rbac_and_tenant_isolation.py

if [ -d "$ROOT/frontend/node_modules" ]; then
  echo "== US-027 identity access e2e =="
  (cd "$ROOT/frontend" && npx playwright test e2e/identity-access.spec.ts)
fi

echo "== US-027 identity access verify complete =="
