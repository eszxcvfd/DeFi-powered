#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
./scripts/verify-us-002.sh
echo "== US-003 source policy registry verify complete =="