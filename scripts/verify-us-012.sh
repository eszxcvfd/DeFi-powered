#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-}:src"
PY="${ROOT}/.venv/bin/python"
[ -x "$PY" ] || PY=python3

./scripts/verify-us-011.sh

echo "== US-012 lead pipeline unit + integration =="
"$PY" -m pytest -q tests/unit/test_lead_pipeline.py tests/integration/test_lead_pipeline_api.py

echo "== US-012 lead pipeline verify complete =="