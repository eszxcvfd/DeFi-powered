#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
./scripts/verify-us-003.sh
echo "== US-004 discovery lifecycle verify complete =="