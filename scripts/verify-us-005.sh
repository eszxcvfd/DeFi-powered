#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-}:src"
PY="${ROOT}/.venv/bin/python"
[ -x "$PY" ] || PY=python3

./scripts/verify-us-004.sh

echo "== US-005 event review unit + integration =="
"$PY" -m pytest -q \
  tests/unit/test_event_deduplication.py \
  tests/unit/test_event_confidence.py \
  tests/integration/test_events_review_api.py

echo "== US-005 event results verify complete =="