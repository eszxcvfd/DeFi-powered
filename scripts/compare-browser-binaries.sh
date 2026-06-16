#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="${PYTHONPATH:-}:$ROOT/src"
exec "$ROOT/.venv/bin/python" "$ROOT/scripts/compare_browser_binaries.py"