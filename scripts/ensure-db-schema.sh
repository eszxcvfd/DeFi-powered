#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-}:src"
ALEMBIC="${ROOT}/.venv/bin/alembic"
PY="${ROOT}/.venv/bin/python"
[ -x "$ALEMBIC" ] || ALEMBIC=alembic
[ -x "$PY" ] || PY=python3

STAMP="$("$PY" <<'PY'
import sqlite3
import sys
from pathlib import Path
from livelead.runtime.settings import parse_settings

path = Path(parse_settings().sqlite_path)
if not path.exists():
    sys.exit(2)
conn = sqlite3.connect(path)
tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
if "organizations" not in tables:
    conn.close()
    sys.exit(2)
if "alembic_version" in tables:
    row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
    if row and row[0]:
        conn.close()
        sys.exit(2)
conn.close()
print("20260614_0002" if "events" in tables else "20260613_0001")
PY
)" || true

if [ -n "${STAMP:-}" ]; then
  echo "legacy sqlite: stamping $STAMP"
  "$ALEMBIC" stamp "$STAMP"
fi

"$ALEMBIC" upgrade head
echo "== ensure-db-schema complete =="