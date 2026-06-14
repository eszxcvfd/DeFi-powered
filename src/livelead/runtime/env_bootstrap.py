"""Load optional env files before AppSettings (repo root .env is handled by pydantic)."""

from __future__ import annotations

import os
import re
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_playwright_browser_env() -> None:
    """Apply frontend/.playwright-browser.env (from scripts/playwright-install.sh)."""
    path = repo_root() / "frontend" / ".playwright-browser.env"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"export\s+(\w+)=(.*)$", line)
        if not m:
            continue
        key, raw = m.group(1), m.group(2).strip()
        if (raw.startswith("'") and raw.endswith("'")) or (
            raw.startswith('"') and raw.endswith('"')
        ):
            raw = raw[1:-1]
        if key not in os.environ:
            os.environ[key] = raw


def load_repo_dotenv() -> None:
    """Load repo-root `.env` into os.environ (setdefault) so workers work regardless of CWD."""
    path = repo_root() / ".env"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, raw = line.partition("=")
        key = key.strip()
        if not key.startswith("LIVELEAD_"):
            continue
        value = raw.strip()
        if (value.startswith("'") and value.endswith("'")) or (
            value.startswith('"') and value.endswith('"')
        ):
            value = value[1:-1]
        os.environ.setdefault(key, value)


def ensure_env_loaded() -> None:
    load_repo_dotenv()
    load_playwright_browser_env()
