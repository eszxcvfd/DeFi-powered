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
    cloakbrowser_kill_switch: bool = Field(
        default=False,
        description="When true, CloakBrowser engine use is blocked globally (US-025)",
    )
    cloakbrowser_pinned_version: str | None = Field(
        default=None,
        description="Globally pinned CloakBrowser runtime version for policy checks",
    )
    cloakbrowser_runtime_version: str | None = Field(
        default=None,
        description="Observed CloakBrowser runtime version for checksum/pin checks",
    )
    cloakbrowser_expected_checksum: str | None = Field(
        default=None,
        description="Expected CloakBrowser artifact checksum when verification is enabled",
    )
    cloakbrowser_runtime_checksum: str | None = Field(
        default=None,
        description="Observed CloakBrowser artifact checksum at runtime",
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
    discovery_copilot_provider: str = Field(
        default="deterministic",
        description="discovery copilot backend: deterministic | gemini (Google AI Studio)",
    )
    google_ai_studio_api_key: str | None = Field(
        default=None,
        description="Google AI Studio API key for Gemini discovery copilot",
    )
    gemini_model: str = Field(
        default="gemini-2.0-flash",
        description="Gemini model id when discovery_copilot_provider=gemini",
    )
    expose_e2e_discovery_rss_fixture: bool = Field(
        default=False,
        description="Serve /dev/e2e-discovery-rss for Playwright US-032 proof only",
    )
    expose_e2e_discovery_website_fixture: bool = Field(
        default=False,
        description="Serve /dev/e2e-discovery-website HTML for US-033 Playwright proof",
    )
    auth_session_ttl_seconds: int = Field(
        default=8 * 60 * 60,
        description="Default session lifetime in seconds (US-027)",
    )
    auth_cookie_secure: bool = Field(
        default=False,
        description="Set the Secure flag on the session cookie (enable behind TLS)",
    )
    auth_allow_dev_headers: bool = Field(
        default=True,
        description=(
            "Allow the legacy X-Organization-Id / X-Actor-Role fallback when "
            "no session is present. Tests and e2e keep this on; production "
            "should turn it off (US-027)."
        ),
    )
    auth_default_owner_email: str = Field(
        default="owner@example.com",
        description="Bootstrap owner email (US-027).",
    )
    auth_default_owner_password: str = Field(
        default="Owner-Pass-2026",
        description="Bootstrap owner password (US-027).",
    )
    auth_default_owner_name: str = Field(
        default="LiveLead Owner",
        description="Bootstrap owner display name (US-027).",
    )
    auth_default_organization_id: str = Field(
        default="00000000-0000-4000-8000-000000000001",
        description="Organization used by the bootstrap owner (US-027).",
    )
    auth_rate_limit_threshold: int = Field(
        default=5,
        description="Failed login attempts per window before lockout (US-027).",
    )
    auth_rate_limit_window_seconds: int = Field(
        default=60,
        description="Sliding window in seconds for the login rate limiter (US-027).",
    )
    auth_rate_limit_lockout_seconds: int = Field(
        default=15 * 60,
        description="Lockout duration in seconds for the login rate limiter (US-027).",
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
