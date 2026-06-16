#!/usr/bin/env bash
# Keeps API (8000) + discovery worker + Vite preview (4173) alive for Playwright.
# Playwright webServer runs this script; premature exit causes ECONNREFUSED on /campaigns, /reminders, etc.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-}:src"
export LIVELEAD_SQLITE_PATH="${LIVELEAD_SQLITE_PATH:-$ROOT/data/livelead.sqlite3}"
export LIVELEAD_BROWSER_AUTOMATION_MODE="${LIVELEAD_BROWSER_AUTOMATION_MODE:-playwright}"
# Default false so live-feed e2e (US-032) can hit fixture RSS; website e2e (US-033) sets true in verify script.
export LIVELEAD_DISCOVERY_USE_MOCK_CONNECTORS="${LIVELEAD_DISCOVERY_USE_MOCK_CONNECTORS:-false}"
export LIVELEAD_EXPOSE_E2E_DISCOVERY_RSS_FIXTURE=true
export LIVELEAD_EXPOSE_E2E_DISCOVERY_WEBSITE_FIXTURE=true
if [ -f "$ROOT/frontend/.playwright-browser.env" ]; then
  # shellcheck source=/dev/null
  source "$ROOT/frontend/.playwright-browser.env"
fi

PY="${ROOT}/.venv/bin/python"
UV="${ROOT}/.venv/bin/uvicorn"
DRAM="${ROOT}/.venv/bin/dramatiq"
[ -x "$PY" ] || PY=python3
[ -x "$UV" ] || UV=uvicorn
[ -x "$DRAM" ] || DRAM=dramatiq

API_PORT="${E2E_API_PORT:-8000}"
PREVIEW_PORT="${E2E_PREVIEW_PORT:-4173}"
API_PID=""
WORKER_PID=""
PREVIEW_PID=""

free_port() {
  local port=$1
  if command -v fuser >/dev/null 2>&1; then
    fuser -k "${port}/tcp" 2>/dev/null || true
    sleep 0.5
  elif command -v lsof >/dev/null 2>&1; then
    local pids
    pids=$(lsof -ti ":${port}" 2>/dev/null || true)
    if [ -n "$pids" ]; then
      kill $pids 2>/dev/null || true
      sleep 0.5
    fi
  fi
}

cleanup() {
  kill "$API_PID" "$WORKER_PID" "$PREVIEW_PID" 2>/dev/null || true
  wait "$API_PID" "$WORKER_PID" "$PREVIEW_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

./scripts/migrate-db.sh

if [ -x "$PY" ] || command -v "$PY" >/dev/null 2>&1; then
  "$PY" scripts/clean-e2e.py >&2 || true
fi

free_port "$API_PORT"

"$UV" apps.api.main:app --host 127.0.0.1 --port "$API_PORT" &
API_PID=$!
"$DRAM" apps.worker.discovery_tasks --processes 1 --threads 1 &
WORKER_PID=$!

if command -v docker >/dev/null 2>&1; then
  docker compose up -d redis 2>/dev/null || true
  sleep 1
fi

echo "e2e-with-api: waiting for API on 127.0.0.1:${API_PORT} (pid ${API_PID})..." >&2
for i in $(seq 1 80); do
  if curl -sf "http://127.0.0.1:${API_PORT}/health" >/dev/null; then
    break
  fi
  if ! kill -0 "$API_PID" 2>/dev/null; then
    echo "e2e-with-api: API process exited before health check (iteration ${i})" >&2
    exit 1
  fi
  sleep 0.25
done
if ! curl -sf "http://127.0.0.1:${API_PORT}/health" >/dev/null; then
  echo "e2e-with-api: API failed to start on 127.0.0.1:${API_PORT}" >&2
  exit 1
fi

free_port "$PREVIEW_PORT"

cd "$ROOT/frontend"
echo "e2e-with-api: building frontend for preview..." >&2
npm run build
echo "e2e-with-api: starting Vite preview on 127.0.0.1:${PREVIEW_PORT}..." >&2
npm run preview -- --host 127.0.0.1 --port "$PREVIEW_PORT" &
PREVIEW_PID=$!

for i in $(seq 1 80); do
  if curl -sf "http://127.0.0.1:${PREVIEW_PORT}/" >/dev/null; then
    echo "e2e-with-api: preview ready (pid ${PREVIEW_PID})" >&2
    break
  fi
  if ! kill -0 "$PREVIEW_PID" 2>/dev/null; then
    echo "e2e-with-api: preview process exited before ready (iteration ${i})" >&2
    exit 1
  fi
  sleep 0.25
done
if ! curl -sf "http://127.0.0.1:${PREVIEW_PORT}/" >/dev/null; then
  echo "e2e-with-api: preview failed on 127.0.0.1:${PREVIEW_PORT}" >&2
  exit 1
fi

# Block until preview exits (Playwright stops webServer when tests finish).
wait "$PREVIEW_PID"