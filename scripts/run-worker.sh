#!/usr/bin/env bash
# Discovery worker — always loads repo-root .env (see env_bootstrap.load_repo_dotenv).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-}:src"

DRAM="${ROOT}/.venv/bin/dramatiq"
[ -x "$DRAM" ] || DRAM=dramatiq

# Log effective discovery mode once at startup
"${ROOT}/.venv/bin/python" -c "
from livelead.runtime.settings import parse_settings
s = parse_settings()
print('run-worker: LIVELEAD_DISCOVERY_USE_MOCK_CONNECTORS=', s.discovery_use_mock_connectors, file=__import__('sys').stderr)
print('run-worker: sqlite=', s.sqlite_path.resolve(), file=__import__('sys').stderr)
" 2>&1 || true

exec "$DRAM" apps.worker.tasks --processes 1 --threads 1