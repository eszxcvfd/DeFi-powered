#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-}:src"
if [ -x "$ROOT/.venv/bin/python" ]; then
  PY="$ROOT/.venv/bin/python"
else
  PY="python3"
fi

echo "== ruff =="
"$PY" -m ruff check apps src tests

echo "== pytest =="
"$PY" -m pytest -q

echo "== alembic env =="
"$PY" -c "from alembic.config import Config; from livelead.runtime.settings import parse_settings; parse_settings(); Config('alembic.ini'); print('alembic env ok')"

echo "== frontend build =="
npm --prefix frontend run build

echo "== frontend component test (shell) =="
npm --prefix frontend run test

echo "== playwright install (required) =="
./scripts/playwright-install.sh
if [ -f "$ROOT/frontend/.playwright-browser.env" ]; then
  # shellcheck source=/dev/null
  source "$ROOT/frontend/.playwright-browser.env"
fi

echo "== frontend playwright e2e (required) =="
npm --prefix frontend run test:e2e

echo "== redis =="
if command -v docker >/dev/null 2>&1; then
  docker compose up -d redis
  sleep 2
else
  echo "docker not found — skip compose redis (worker smoke may fail)"
fi

echo "== smoke-api =="
./scripts/smoke-api.sh

echo "== smoke-worker =="
./scripts/smoke-worker.sh

echo "== smoke-scheduler =="
./scripts/smoke-scheduler.sh

echo "== smoke-browser-worker =="
./scripts/smoke-browser-worker.sh

echo "== foundation verify complete =="