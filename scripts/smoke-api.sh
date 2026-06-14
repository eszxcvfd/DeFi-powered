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
import json
import os
import socket
import time
import urllib.request
from subprocess import Popen

def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

os.environ.setdefault('LIVELEAD_SQLITE_PATH', 'data/livelead.sqlite3')
port = free_port()
uv = '$ROOT/.venv/bin/uvicorn' if os.path.isfile('$ROOT/.venv/bin/uvicorn') else 'uvicorn'
proc = Popen([uv, 'apps.api.main:app', '--host', '127.0.0.1', '--port', str(port)])
url = f'http://127.0.0.1:{port}/health'
try:
    for _ in range(30):
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                data = json.loads(resp.read().decode())
            break
        except Exception:
            time.sleep(0.2)
    else:
        raise SystemExit('health endpoint did not become ready')
    assert data.get('service') == 'livelead-api', data
    print('smoke-api ok', data.get('status'), 'port', port)
finally:
    proc.terminate()
    proc.wait(timeout=10)
"