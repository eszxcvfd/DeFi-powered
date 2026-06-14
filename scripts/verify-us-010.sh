#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-}:src"
PY="${ROOT}/.venv/bin/python"
[ -x "$PY" ] || PY=python3

./scripts/verify-us-009.sh

echo "== US-010 content approval unit + integration =="
"$PY" -m pytest -q tests/unit/test_content_review.py tests/integration/test_content_approval_api.py

echo "== US-010 content approval verify complete =="