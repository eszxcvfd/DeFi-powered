#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-}:src"
PY="${ROOT}/.venv/bin/python"
[ -x "$PY" ] || PY=python3

./scripts/verify-us-006.sh

echo "== US-007 audience unit + integration =="
"$PY" -m pytest -q tests/unit/test_audience_generator.py tests/integration/test_audience_api.py

echo "== US-007 audience hypothesis verify complete =="