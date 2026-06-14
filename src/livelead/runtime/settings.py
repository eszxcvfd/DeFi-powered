"""Application settings parsed at the process boundary."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_sqlite_path() -> Path:
    return Path("data/livelead.sqlite3")


def _resolved_env_file() -> Path | None:
    from livelead.runtime.env_bootstrap import repo_root

    path = repo_root() / ".env"
    return path if path.is_file() else None


class AppSettings(BaseSettings):
    """Typed bootstrap for local and single-host MVP."""

    model_config = SettingsConfigDict(
        env_prefix="LIVELEAD_",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = Field(default="development", description="Runtime mode label")
    sqlite_path: Path = Field(default_factory=_default_sqlite_path)
    redis_url: str = Field(default="redis://127.0.0.1:6379/0")
    api_host: str = Field(default="127.0.0.1")
    api_port: int = Field(default=8000)
    secret_master_key: str = Field(
        default="dev-only-change-in-production-livelead",
        description="Fernet key material for connector secrets at rest",
    )
    browser_automation_mode: str = Field(
        default="playwright",
        description="playwright | cloakbrowser (same runtime, different binary) | stub (tests only)",
    )
    browser_headless: bool = Field(default=True)
    browser_navigation_timeout_ms: int = Field(default=45_000)
    playwright_chromium_executable: str | None = Field(
        default=None,
        description="Optional Chrome/Chromium path (e.g. from scripts/playwright-install.sh)",
    )
    cloakbrowser_executable: str | None = Field(
        default=None,
        description="Optional CloakBrowser/Chromium binary for cloakbrowser engine connectors",
    )
    browser_profile_root: Path = Field(
        default_factory=lambda: Path("data/browser_profiles"),
        description="Per-session isolated profile storage root",
    )
    artifact_root: Path = Field(
        default_factory=lambda: Path("data"),
        description="Root for browser debug artifact blobs (under browser_artifacts/)",
    )
    discovery_use_mock_connectors: bool = Field(
        default=False,
        description="If true, discovery uses deterministic mock sources (tests only)",
    )

    @property
    def database_url(self) -> str:
        path = self.sqlite_path.resolve()
        return f"sqlite+aiosqlite:///{path}"


def parse_settings() -> AppSettings:
    from livelead.runtime.env_bootstrap import ensure_env_loaded

    ensure_env_loaded()
    env_file = _resolved_env_file()
    if env_file is not None:
        return AppSettings(_env_file=env_file)  # type: ignore[call-arg]
    return AppSettings()
