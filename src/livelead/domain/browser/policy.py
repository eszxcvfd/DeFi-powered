"""Browser launch policy — composes source governance checks."""

from livelead.domain.browser.models import BrowserEngine, LaunchContextKind
from livelead.domain.sources.models import ConnectorType, PolicyDecision, SourceGovernance


class BrowserLaunchDenied(Exception):
    def __init__(self, reasons: tuple[str, ...]) -> None:
        self.reasons = reasons
        super().__init__("browser launch denied: " + ", ".join(reasons))


def _source_allows_browser(source: SourceGovernance) -> bool:
    if source.connector_type == ConnectorType.BROWSER:
        return True
    return source.policy.access_mode.value == "browser"


def evaluate_browser_launch(
    source: SourceGovernance,
    decision: PolicyDecision,
    *,
    target_kind: LaunchContextKind,
) -> tuple[BrowserEngine, tuple[str, ...]]:
    reasons: list[str] = []
    if target_kind not in (LaunchContextKind.EVENT, LaunchContextKind.SOURCE):
        reasons.append("invalid_target_kind")
    if not _source_allows_browser(source):
        reasons.append("source_not_browser_capable")
    if not decision.runnable:
        reasons.extend(decision.reasons or ("policy_denied",))

    engine_raw = (source.automation_engine or "playwright").lower()
    if engine_raw in ("selenium",):
        engine = BrowserEngine.SELENIUM
    elif engine_raw in ("cloakbrowser", "cloak"):
        engine = BrowserEngine.CLOAKBROWSER
    elif engine_raw in ("playwright", "none", ""):
        engine = BrowserEngine.PLAYWRIGHT
    else:
        engine = BrowserEngine.STUB

    if reasons:
        raise BrowserLaunchDenied(tuple(dict.fromkeys(reasons)))
    return engine, tuple()
