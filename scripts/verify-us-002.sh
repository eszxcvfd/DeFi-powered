#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
./scripts/verify-foundation.sh
echo "== US-002 campaign contract verify complete =="