#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-}:src"
PY="${ROOT}/.venv/bin/python"
[ -x "$PY" ] || PY=python3

./scripts/verify-us-008.sh

echo "== US-009 content unit + integration =="
"$PY" -m pytest -q tests/unit/test_content_risk.py tests/integration/test_content_api.py

echo "== US-009 content generation verify complete =="