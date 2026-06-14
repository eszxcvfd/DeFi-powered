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
exec "$PY" -c "
import dramatiq
from livelead.runtime.settings import parse_settings
from livelead.infrastructure.queue.broker import configure_broker, ping_redis
import apps.worker.tasks  # registers actors

settings = parse_settings()
if not ping_redis(settings):
    raise SystemExit('Redis unavailable — run: docker compose up -d redis')
configure_broker(settings)
assert dramatiq.get_broker() is not None
print('smoke-worker ok', type(dramatiq.get_broker()).__name__)
"