#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-}:src"
PY="${ROOT}/.venv/bin/python"
[ -x "$PY" ] || PY=python3

./scripts/verify-us-004.sh

echo "== US-006 scoring unit =="
"$PY" -m pytest -q tests/unit/test_scoring_calculator.py tests/integration/test_events_scoring_api.py

echo "== US-006 event scoring verify complete =="