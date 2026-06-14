#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-}:src"
PY="${ROOT}/.venv/bin/python"
[ -x "$PY" ] || PY=python3

# Full chain through US-010, including verify-foundation (platform + full e2e suite).
./scripts/verify-us-010.sh

echo "== US-011 content handoff unit + integration =="
"$PY" -m pytest -q tests/unit/test_content_handoff.py tests/integration/test_content_handoff_api.py

echo "== US-011 content handoff verify complete =="