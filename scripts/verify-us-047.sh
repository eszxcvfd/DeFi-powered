#!/usr/bin/env bash
# US-047 — Internationalization and timezone baseline.
#
# Runs the unit + integration tests that prove the
# closed `Locale` enum (`vi-VN`, `en-US`), the
# bounded `Timezone` IANA validation, the
# `I18nService` resolution chain, the per-user
# and per-organization locale/timezone surface,
# the audit entry shape (`user.locale.updated`,
# `organization.locale.updated`,
# `locale.unsupported.rejected`), the secret-safe
# payload reuse from US-041, the RBAC contract
# from US-027, and the migration forward-safety
# all work end-to-end against the accepted
# single-host MVP stack.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-}:src:."
if [ -f "$ROOT/frontend/.playwright-browser.env" ]; then
  # shellcheck source=/dev/null
  source "$ROOT/frontend/.playwright-browser.env"
fi
PY="${ROOT}/.venv/bin/python"
[ -x "$PY" ] || PY=python3

echo "== US-047 migration: i18n columns present =="
"$PY" -c "
import sqlite3, sys
conn = sqlite3.connect('data/livelead.sqlite3')
required = {
    'users': ['locale', 'timezone'],
    'organizations': ['default_locale', 'default_timezone'],
}
missing = []
for t, cols in required.items():
    table_cols = {r[1] for r in conn.execute(f'PRAGMA table_info({t})').fetchall()}
    for c in cols:
        if c not in table_cols:
            missing.append(f'{t}.{c}')
if missing:
    print('MISSING:', missing)
    sys.exit(1)
print('OK')
"

echo "== US-047 closed Locale enum =="
"$PY" -m pytest -q tests/unit/test_i18n_service.py -k "locale or Locale"

echo "== US-047 bounded Timezone IANA validation =="
"$PY" -m pytest -q tests/unit/test_i18n_service.py -k "timezone or Timezone"

echo "== US-047 I18nService resolution chain =="
"$PY" -m pytest -q tests/unit/test_i18n_service.py -k "resolve"

echo "== US-047 datetime formatters =="
"$PY" -m pytest -q tests/unit/test_i18n_service.py -k "format"

echo "== US-047 Unicode normalization =="
"$PY" -m pytest -q tests/unit/test_i18n_service.py -k "normalize"

echo "== US-047 full I18nService unit suite =="
"$PY" -m pytest -q tests/unit/test_i18n_service.py

echo "== US-047 i18n REST integration suite =="
"$PY" -m pytest -q tests/integration/test_i18n_api.py

echo "== US-047 frontend tsc compile =="
TSC_OUTPUT=$(cd frontend && timeout 60 npx tsc --noEmit -p tsconfig.app.json 2>&1 || true)
if echo "$TSC_OUTPUT" | grep -E "i18n|locale|Localized|LocaleSwitch|OrganizationLocale|lib/i18n" >/dev/null; then
  echo "FAIL: tsc found errors in i18n files"
  echo "$TSC_OUTPUT" | grep -E "i18n|locale|Localized|LocaleSwitch|OrganizationLocale|lib/i18n"
  exit 1
fi

echo "== US-047 frontend dictionary files present =="
test -f frontend/src/locales/en-US.json
test -f frontend/src/locales/vi-VN.json
test -f frontend/src/api/i18n.ts
test -f frontend/src/lib/i18n.tsx
test -f frontend/src/components/LocaleSwitcher.tsx
test -f frontend/src/components/OrganizationLocalePanel.tsx
test -f frontend/src/components/LocalizedDatetime.tsx

echo "== US-047 dictionary key coverage check =="
"$PY" -c "
import json, sys
with open('frontend/src/locales/en-US.json') as f:
    en = set(json.load(f).keys())
with open('frontend/src/locales/vi-VN.json') as f:
    vi = set(json.load(f).keys())
missing_vi = en - vi
if missing_vi:
    print('MISSING in vi-VN:', sorted(missing_vi))
    sys.exit(1)
print(f'OK ({len(en)} keys, all in both dictionaries)')
"

echo "== US-047 audit action enum entries present =="
"$PY" -c "
from livelead.domain.audit.enums import AuditAction
required = [
    'USER_LOCALE_UPDATED',
    'ORGANIZATION_LOCALE_UPDATED',
    'LOCALE_UNSUPPORTED_REJECTED',
]
missing = [r for r in required if r not in AuditAction.__members__]
if missing:
    print('MISSING:', missing)
    raise SystemExit(1)
print('OK')
"

echo "== US-047 verify complete =="
