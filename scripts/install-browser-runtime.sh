#!/usr/bin/env bash
# Install Python Playwright + browser binary for real supervised sessions (US-020).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="${ROOT}/.venv/bin/pip"
[ -x "$PY" ] || PY=pip3
"$PY" install 'playwright>=1.49.0'
"${ROOT}/.venv/bin/python" -m playwright install chromium 2>/dev/null || true
./scripts/playwright-install.sh
echo "== Browser runtime: LIVELEAD_BROWSER_AUTOMATION_MODE=playwright (default) =="
echo "== Optional CloakBrowser: LIVELEAD_CLOAKBROWSER_EXECUTABLE=/path/to/chromium =="