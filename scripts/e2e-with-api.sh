#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-}:src"
PY="${ROOT}/.venv/bin/python"
UV="${ROOT}/.venv/bin/uvicorn"
DRAM="${ROOT}/.venv/bin/dramatiq"
[ -x "$PY" ] || PY=python3
[ -x "$UV" ] || UV=uvicorn
[ -x "$DRAM" ] || DRAM=dramatiq

./scripts/migrate-db.sh

"$UV" apps.api.main:app --host 127.0.0.1 --port 8000 &
API_PID=$!
"$DRAM" apps.worker.discovery_tasks --processes 1 --threads 1 &
WORKER_PID=$!
trap 'kill $API_PID $WORKER_PID 2>/dev/null || true' EXIT

if command -v docker >/dev/null 2>&1; then
  docker compose up -d redis 2>/dev/null || true
  sleep 1
fi

for i in $(seq 1 40); do
  curl -sf http://127.0.0.1:8000/health >/dev/null && break
  sleep 0.25
done

cd "$ROOT/frontend"
npm run preview -- --host 127.0.0.1 --port 4173