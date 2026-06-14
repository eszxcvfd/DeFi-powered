#!/usr/bin/env bash
# US-001: Playwright e2e is mandatory.
# - "playwright install chromium" = Playwright's own browser download (may fail on Ubuntu 26).
# - Google Chrome / Chromium you installed system-wide is still used via PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND="$ROOT/frontend"
ENV_FILE="$FRONTEND/.playwright-browser.env"

cd "$FRONTEND"
rm -f "$ENV_FILE"

resolve_browser() {
  local candidate path
  for candidate in \
    google-chrome-stable \
    google-chrome \
    chromium-browser \
    chromium \
    microsoft-edge-stable; do
    if path="$(command -v "$candidate" 2>/dev/null)"; then
      echo "$path"
      return 0
    fi
  done
  for path in \
    /usr/bin/google-chrome-stable \
    /usr/bin/google-chrome \
    /usr/bin/chromium-browser \
    /usr/bin/chromium \
    /snap/bin/chromium; do
    if [ -x "$path" ]; then
      echo "$path"
      return 0
    fi
  done
  return 1
}

write_system_browser_env() {
  local browser_path="$1"
  printf 'export PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=%q\n' "$browser_path" >"$ENV_FILE"
  echo "playwright: using system browser (Google Chrome/Chromium): $browser_path"
  echo "  (Playwright bundled Chromium is optional; your installed browser is valid for e2e.)"
}

# If Chrome/Chromium is already on PATH, use it when bundled install is unsupported.
if BROWSER_PATH="$(resolve_browser)"; then
  if ! npm exec playwright install chromium >/dev/null 2>&1; then
    write_system_browser_env "$BROWSER_PATH"
    exit 0
  fi
  echo "playwright: bundled chromium installed"
  exit 0
fi

# No system browser yet — try bundled download only.
if npm exec playwright install chromium 2>&1; then
  echo "playwright: bundled chromium installed"
  exit 0
fi

echo "playwright: bundled chromium install failed — no system Chrome/Chromium found" >&2
cat >&2 <<'EOF'

Google Chrome can be installed but Playwright still needs a browser binary on PATH.

Install one of:
  - Google Chrome (.deb from Google) — then re-run this script
  - sudo apt install chromium-browser

Or set before verify:
  export PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/path/to/chrome

Note: "Playwright does not support chromium on ubuntu26.04" refers to Playwright's
downloaded Chromium, not to Google Chrome you installed separately.
EOF
exit 1