#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-}:src"
PY="${ROOT}/.venv/bin/python"
[ -x "$PY" ] || PY=python3

./scripts/verify-us-007.sh

echo "== US-008 engagement unit + integration =="
"$PY" -m pytest -q tests/unit/test_engagement_generator.py tests/integration/test_engagement_api.py

echo "== US-008 engagement plan verify complete =="