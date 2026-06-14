#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-}:src"
ALEMBIC="${ROOT}/.venv/bin/alembic"
[ -x "$ALEMBIC" ] || ALEMBIC=alembic
./scripts/ensure-db-schema.sh