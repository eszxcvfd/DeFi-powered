"""Application settings parsed at the process boundary."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_sqlite_path() -> Path:
    return Path("data/livelead.sqlite3")


class AppSettings(BaseSettings):
    """Typed bootstrap for local and single-host MVP."""

    model_config = SettingsConfigDict(
        env_prefix="LIVELEAD_",
        env_file=".env",
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

    @property
    def database_url(self) -> str:
        path = self.sqlite_path.resolve()
        return f"sqlite+aiosqlite:///{path}"


def parse_settings() -> AppSettings:
    return AppSettings()