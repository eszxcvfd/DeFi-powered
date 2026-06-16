"""Policy and recipe readiness for browser discovery connectors (US-033/US-034)."""

from __future__ import annotations

from livelead.domain.discovery.browser_recipe import parse_browser_discovery_recipe
from livelead.domain.discovery.models import SourceRunStatus
from livelead.domain.sources.models import (
    AuthenticationMode,
    ConnectorType,
    PolicyDecision,
    SourceGovernance,
)

_PLAYWRIGHT_ENGINES = frozenset({"playwright", "none", ""})
_SELENIUM_ENGINES = frozenset({"selenium"})


def browser_connector_family(automation_engine: str | None) -> str:
    engine = (automation_engine or "playwright").lower()
    if engine in _SELENIUM_ENGINES:
        return "selenium_website"
    return "playwright_website"


def browser_execution_mode(*, use_mock: bool, automation_engine: str | None) -> str:
    if use_mock:
        return "mock"
    engine = (automation_engine or "playwright").lower()
    if engine in _SELENIUM_ENGINES:
        return "selenium_website"
    return "playwright_website"


def resolve_browser_discovery_run(
    source: SourceGovernance,
    decision: PolicyDecision,
    *,
    rate_limit_json: str | None,
) -> tuple[SourceRunStatus, str | None, str | None]:
    """Whether an approved browser connector may run automated discovery."""
    family = browser_connector_family(source.automation_engine)

    if source.connector_type != ConnectorType.BROWSER:
        return (
            SourceRunStatus.FAILED,
            f"connector_type_{source.connector_type.value}_not_browser_discovery",
            family,
        )

    if not decision.runnable:
        return (
            SourceRunStatus.FAILED,
            "policy_denied:" + ",".join(decision.reasons),
            family,
        )

    engine = (source.automation_engine or "none").lower()
    if engine == "cloakbrowser":
        return (
            SourceRunStatus.FAILED,
            "cloakbrowser_not_enabled_for_automated_website_discovery",
            family,
        )
    if engine not in _PLAYWRIGHT_ENGINES and engine not in _SELENIUM_ENGINES:
        return (
            SourceRunStatus.FAILED,
            f"automation_engine_{engine}_not_supported_for_website_discovery",
            family,
        )

    if source.authentication_mode != AuthenticationMode.NONE:
        return (
            SourceRunStatus.NEEDS_USER_ACTION,
            "login_required_not_supported_in_discovery_baseline",
            family,
        )

    _recipe, recipe_errors = parse_browser_discovery_recipe(rate_limit_json)
    if recipe_errors:
        return (
            SourceRunStatus.FAILED,
            "recipe_not_ready:" + ",".join(recipe_errors),
            family,
        )

    return SourceRunStatus.PENDING, None, family