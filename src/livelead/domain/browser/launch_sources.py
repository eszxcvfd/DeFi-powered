"""Resolve which registry source may launch a supervised browser session."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from livelead.domain.browser.models import LaunchContextKind
from livelead.domain.browser.policy import BrowserLaunchDenied, evaluate_browser_launch
from livelead.domain.sources.models import AccessMode, ConnectorType, SourceGovernance
from livelead.domain.sources.policy import evaluate_source_policy


@dataclass(frozen=True, slots=True)
class BrowserLaunchSourceOption:
    source_id: UUID
    name: str
    domain: str
    automation_engine: str
    engine: str
    runnable: bool
    denied_reasons: tuple[str, ...]


def source_allows_browser_launch(source: SourceGovernance) -> bool:
    if source.connector_type == ConnectorType.BROWSER:
        return True
    return source.policy.access_mode == AccessMode.BROWSER


def _engine_label(source: SourceGovernance) -> str:
    raw = (source.automation_engine or "playwright").lower()
    if raw in ("cloakbrowser", "cloak"):
        return "cloakbrowser"
    if raw == "selenium":
        return "selenium"
    return "playwright"


def _try_launchable(source: SourceGovernance) -> BrowserLaunchSourceOption | None:
    if not source_allows_browser_launch(source):
        return None
    decision = evaluate_source_policy(source)
    try:
        engine, _ = evaluate_browser_launch(source, decision, target_kind=LaunchContextKind.EVENT)
        return BrowserLaunchSourceOption(
            source_id=source.id,
            name=source.name,
            domain=source.domain,
            automation_engine=source.automation_engine,
            engine=engine.value,
            runnable=True,
            denied_reasons=(),
        )
    except BrowserLaunchDenied as exc:
        return BrowserLaunchSourceOption(
            source_id=source.id,
            name=source.name,
            domain=source.domain,
            automation_engine=source.automation_engine,
            engine=_engine_label(source),
            runnable=False,
            denied_reasons=exc.reasons,
        )


def list_browser_launch_options(sources: list[SourceGovernance]) -> list[BrowserLaunchSourceOption]:
    out: list[BrowserLaunchSourceOption] = []
    for src in sources:
        opt = _try_launchable(src)
        if opt:
            out.append(opt)
    out.sort(key=lambda o: (0 if o.runnable else 1, o.name.lower()))
    return out


def _is_runnable_launch(source: SourceGovernance) -> bool:
    decision = evaluate_source_policy(source)
    try:
        evaluate_browser_launch(source, decision, target_kind=LaunchContextKind.EVENT)
        return True
    except BrowserLaunchDenied:
        return False


def pick_browser_source_for_event(
    *,
    observation_source_ids: list[UUID],
    campaign_source_ids: list[UUID],
    registry: dict[UUID, SourceGovernance],
) -> UUID | None:
    for sid in observation_source_ids:
        src = registry.get(sid)
        if src and source_allows_browser_launch(src) and _is_runnable_launch(src):
            return sid
    for sid in campaign_source_ids:
        src = registry.get(sid)
        if src and source_allows_browser_launch(src) and _is_runnable_launch(src):
            return sid
    return None
