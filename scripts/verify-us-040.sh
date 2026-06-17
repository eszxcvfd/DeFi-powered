#!/usr/bin/env bash
# US-040 — Real-environment pilot cutover with guarded live operations.
#
# Runs the unit + integration tests that prove the cutover, runtime
# readiness, live toggles, and backup metadata surfaces work end-to-end
# against the accepted single-host MVP stack.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-}:src"
PY="${ROOT}/.venv/bin/python"
[ -x "$PY" ] || PY=python3

echo "== US-040 prerequisite US-026 audit (foundation for cutover audit events) =="
"$PY" -m pytest -q tests/unit/test_audit_log_model.py

echo "== US-040 launch-gate evaluator unit =="
"$PY" -m pytest -q tests/unit/test_runtime_launch_gate.py tests/unit/test_runtime_environment_profile.py

echo "== US-040 live-toggle service unit =="
"$PY" -m pytest -q tests/unit/test_runtime_live_toggles.py

echo "== US-040 backup service unit =="
"$PY" -m pytest -q tests/unit/test_runtime_backup.py

echo "== US-040 cutover service unit =="
"$PY" -m pytest -q tests/unit/test_runtime_cutover.py

echo "== US-040 runtime readiness / live toggles / backups / cutover integration =="
"$PY" -m pytest -q tests/integration/test_runtime_readiness_api.py

echo "== US-040 real-environment pilot cutover verify complete =="
echo
echo "Operator runbooks (US-040 ops evidence):"
echo "  docs/ops/pilot-live-cutover-runbook.md"
echo "  docs/ops/pilot-live-pause-runbook.md"
echo "  docs/ops/pilot-live-rollback-runbook.md"
echo
echo "Update the durable story with:"
echo "  scripts/bin/harness-cli story update --id US-040 --status implemented --unit 1 --integration 1 --e2e 0 --platform 0 --verify ./scripts/verify-us-040.sh"
