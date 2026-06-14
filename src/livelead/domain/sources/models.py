from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class ConnectorType(StrEnum):
    OFFICIAL_API = "official_api"
    RSS = "rss"
    ATOM = "atom"
    SITEMAP = "sitemap"
    ICS = "ics"
    BROWSER = "browser"


class AccessMode(StrEnum):
    API = "api"
    FEED = "feed"
    BROWSER = "browser"


class AuthenticationMode(StrEnum):
    NONE = "none"
    API_KEY = "api_key"
    OAUTH = "oauth"
    SESSION = "session"


@dataclass(frozen=True, slots=True)
class SourcePolicy:
    access_mode: AccessMode
    quota_per_day: int = 1000
    quota_used_today: int = 0
    window_start_hour: int = 0
    window_end_hour: int = 23
    retention_days: int = 90
    valid: bool = True


@dataclass(frozen=True, slots=True)
class SourceGovernance:
    id: UUID
    organization_id: UUID
    name: str
    domain: str
    connector_type: ConnectorType
    automation_engine: str
    authentication_mode: AuthenticationMode
    enabled: bool
    approved: bool
    approved_at: datetime | None
    approved_by: str | None
    policy: SourcePolicy
    has_secret: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    runnable: bool
    reasons: tuple[str, ...] = ()
    preferred_over_browser: bool = False