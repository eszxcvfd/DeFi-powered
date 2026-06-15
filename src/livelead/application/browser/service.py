"""Browser session orchestration (US-020)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.browser.evidence_provisioning import ensure_playwright_source_for_event
from livelead.domain.browser.action_confirmation import (
    BrowserConfirmationState,
    build_action_preview,
    can_cancel,
    can_confirm,
    confirmation_expires_at,
    effective_confirmation_state,
    normalize_submit_form_parameters,
    parse_confirmation_gated_allowlist,
    requires_confirmation,
)
from livelead.domain.browser.action_policy import (
    action_timeout_ms,
    evaluate_action_policy_with_json,
    max_actions_per_session,
    normalize_action_parameters,
    parse_browser_action_allowlist,
)
from livelead.domain.browser.actions import BrowserActionLifecycle, BrowserActionType
from livelead.domain.browser.launch_sources import (
    BrowserLaunchSourceOption,
    list_browser_launch_options,
    pick_browser_source_for_event,
)
from livelead.domain.browser.lifecycle import (
    can_request_stop,
    is_terminal,
    next_state_after_stop_request,
    runtime_seconds,
    validate_launch_target,
)
from livelead.domain.browser.models import (
    BrowserSessionRecord,
    BrowserSessionState,
    BrowserSessionTarget,
    LaunchContextKind,
)
from livelead.domain.browser.policy import BrowserLaunchDenied, evaluate_browser_launch
from livelead.application.cloakbrowser.policy_service import (
    CloakBrowserPolicyBlocked,
    CloakBrowserPolicyService,
)
from livelead.domain.events.source_url_utils import pick_browser_launch_url
from livelead.domain.sources.policy import evaluate_source_policy
from livelead.runtime.settings import AppSettings, parse_settings
from livelead.infrastructure.browser.adapter import (
    execute_confirmation_gated_action,
    execute_read_only_action,
    read_runtime,
    request_stop,
    schedule_session_start,
)
from livelead.infrastructure.db.browser_session_mappers import new_session_row, row_to_record
from livelead.infrastructure.db.repositories.browser_action_confirmations import (
    BrowserActionConfirmationRepository,
)
from livelead.infrastructure.db.repositories.browser_session_actions import (
    BrowserSessionActionRepository,
)
from livelead.infrastructure.db.repositories.browser_sessions import BrowserSessionRepository
from livelead.infrastructure.db.repositories.events import EventRepository
from livelead.infrastructure.db.repositories.sources import SourceRepository
from livelead.infrastructure.db.source_mappers import row_to_source

logger = logging.getLogger("livelead.browser_session")


@dataclass(frozen=True, slots=True)
class InvalidLaunchContext(Exception):
    errors: tuple[str, ...]


class BrowserSessionService:
    def __init__(self, session: AsyncSession, settings: AppSettings | None = None) -> None:
        self._session = session
        self._settings = settings or parse_settings()
        self._repo = BrowserSessionRepository(session)
        self._events = EventRepository(session)
        self._sources = SourceRepository(session)

    async def create_for_event(
        self,
        organization_id: UUID,
        actor: str,
        *,
        event_id: UUID,
        source_id: UUID | None = None,
    ) -> BrowserSessionRecord:
        event, options = await self._launch_context_for_event(organization_id, event_id, actor)
        registry = {s.id: s for s in await self._sources.list_for_organization(organization_id)}
        obs = await self._events.list_observations(event_id)
        campaign_ids = await self._sources.list_campaign_source_ids(
            event.campaign_id, organization_id
        )
        obs_ids = [o.source_id for o in obs]

        resolved_source = source_id
        if resolved_source is not None and resolved_source in registry:
            src = registry[resolved_source]
            if not evaluate_source_policy(src).runnable:
                resolved_source = None
        else:
            resolved_source = None
        if resolved_source is None:
            resolved_source = pick_browser_source_for_event(
                observation_source_ids=obs_ids,
                campaign_source_ids=campaign_ids,
                registry=registry,
            )
        if resolved_source is None:
            runnable = [o for o in options if o.runnable]
            if runnable:
                resolved_source = runnable[0].source_id
        if resolved_source is None:
            raise InvalidLaunchContext(("no_browser_source",))

        src_for_url = registry.get(resolved_source)
        launch_url = pick_browser_launch_url(
            event_source_url=event.source_url,
            observation_urls=[o.source_url for o in obs],
            source_domain=src_for_url.domain if src_for_url else None,
        )

        target = BrowserSessionTarget(
            kind=LaunchContextKind.EVENT,
            event_id=event_id,
            source_id=resolved_source,
            initial_url=launch_url,
            source_name="",
            source_domain="",
        )
        return await self._create(organization_id, actor, target)

    async def list_launch_sources_for_event(
        self, organization_id: UUID, event_id: UUID, *, actor: str = "analyst"
    ) -> list[BrowserLaunchSourceOption]:
        _, options = await self._launch_context_for_event(organization_id, event_id, actor)
        return options

    async def provision_playwright_from_evidence(
        self, organization_id: UUID, event_id: UUID, actor: str
    ) -> list[BrowserLaunchSourceOption]:
        _, options = await self._launch_context_for_event(organization_id, event_id, actor)
        await self._session.commit()
        return options

    async def _launch_context_for_event(
        self, organization_id: UUID, event_id: UUID, actor: str
    ) -> tuple:
        event = await self._events.get(event_id, organization_id)
        if not event:
            raise LookupError("event not found")
        obs = await self._events.list_observations(event_id)
        await ensure_playwright_source_for_event(
            self._session,
            organization_id=organization_id,
            campaign_id=event.campaign_id,
            actor=actor,
            event_source_url=event.source_url,
            observation_urls=[o.source_url for o in obs],
        )
        all_sources = await self._sources.list_for_organization(organization_id)
        campaign_ids = set(
            await self._sources.list_campaign_source_ids(event.campaign_id, organization_id)
        )
        obs_set = {o.source_id for o in obs}
        candidates = [s for s in all_sources if s.id in obs_set or s.id in campaign_ids]
        options = list_browser_launch_options(candidates)
        if not any(o.runnable for o in options):
            domain_opts = list_browser_launch_options(all_sources)
            options = domain_opts
        return event, options

    async def create_for_source(
        self,
        organization_id: UUID,
        actor: str,
        *,
        source_id: UUID,
        initial_url: str,
        browser_profile_id: UUID | None = None,
        isolation_key: str | None = None,
        profile_boundary: str | None = None,
        storage_state: dict | None = None,
    ) -> BrowserSessionRecord:
        target = BrowserSessionTarget(
            kind=LaunchContextKind.SOURCE,
            event_id=None,
            source_id=source_id,
            initial_url=initial_url,
            source_name="",
            source_domain="",
        )
        return await self._create(
            organization_id,
            actor,
            target,
            browser_profile_id=browser_profile_id,
            isolation_key=isolation_key,
            profile_boundary=profile_boundary,
            storage_state=storage_state,
        )

    async def _create(
        self,
        organization_id: UUID,
        actor: str,
        target: BrowserSessionTarget,
        *,
        browser_profile_id: UUID | None = None,
        isolation_key: str | None = None,
        profile_boundary: str | None = None,
        storage_state: dict | None = None,
    ) -> BrowserSessionRecord:
        errors = validate_launch_target(
            kind=target.kind,
            event_id_present=target.event_id is not None,
            source_id_present=True,
            initial_url=target.initial_url,
        )
        if errors:
            raise InvalidLaunchContext(errors)

        src_row = await self._sources.get(target.source_id, organization_id)
        if not src_row:
            raise InvalidLaunchContext(("source_not_found",))
        source = row_to_source(src_row)
        decision = evaluate_source_policy(source)
        try:
            cloak_svc = CloakBrowserPolicyService(self._session, self._settings)
            await cloak_svc.assert_launch_allowed(
                organization_id,
                target.source_id,
                source.automation_engine,
            )
        except CloakBrowserPolicyBlocked as exc:
            logger.info(
                "browser_session cloakbrowser_denied org=%s source=%s actor=%s reasons=%s",
                organization_id,
                target.source_id,
                actor,
                exc.reasons,
            )
            raise BrowserLaunchDenied(exc.reasons) from exc
        try:
            engine, _ = evaluate_browser_launch(
                source,
                decision,
                target_kind=target.kind,
            )
        except BrowserLaunchDenied as exc:
            logger.info(
                "browser_session denied org=%s source=%s actor=%s reasons=%s",
                organization_id,
                target.source_id,
                actor,
                exc.reasons,
            )
            raise

        enriched = BrowserSessionTarget(
            kind=target.kind,
            event_id=target.event_id,
            source_id=target.source_id,
            initial_url=target.initial_url.strip(),
            source_name=source.name,
            source_domain=source.domain,
        )
        row = new_session_row(
            organization_id=organization_id,
            actor=actor,
            target=enriched,
            engine=engine,
            browser_profile_id=browser_profile_id,
            isolation_key=isolation_key,
            profile_boundary=profile_boundary,
        )
        record = await self._repo.add(row)
        schedule_session_start(
            session_id=record.id,
            organization_id=organization_id,
            engine=engine,
            initial_url=enriched.initial_url,
            isolation_key=record.isolation.isolation_key,
            storage_state=storage_state,
        )
        logger.info(
            "browser_session created id=%s org=%s actor=%s kind=%s source=%s engine=%s",
            record.id,
            organization_id,
            actor,
            target.kind.value,
            target.source_id,
            engine.value,
        )
        return record

    async def get_status(
        self, session_id: UUID, organization_id: UUID
    ) -> BrowserSessionRecord | None:
        row = await self._repo.get(session_id, organization_id)
        if not row:
            return None
        await self._sync_runtime(row)
        return row_to_record(row)

    async def stop(
        self, session_id: UUID, organization_id: UUID, actor: str
    ) -> BrowserSessionRecord:
        row = await self._repo.get(session_id, organization_id)
        if not row:
            raise LookupError("session not found")
        state = BrowserSessionState(row.status)
        if not can_request_stop(state, stop_requested=bool(row.stop_requested)):
            raise ValueError("session not stoppable")
        if state == BrowserSessionState.STOPPING and row.stop_requested:
            await self._sync_runtime(row)
            return row_to_record(row)

        next_state_after_stop_request(state)
        await self._repo.mark_stop_requested(row)
        runtime = request_stop(session_id)
        if runtime:
            await self._apply_runtime_dict(row, runtime)
        await self._session.flush()
        logger.info(
            "browser_session stop id=%s org=%s actor=%s state=%s",
            session_id,
            organization_id,
            actor,
            row.status,
        )
        return row_to_record(row)

    async def request_confirmation_gated_action(
        self,
        session_id: UUID,
        organization_id: UUID,
        actor: str,
        *,
        action_type: BrowserActionType,
        parameters: dict,
    ) -> dict:
        if not requires_confirmation(action_type):
            raise ValueError("action does not require confirmation")
        row = await self._repo.get(session_id, organization_id)
        if not row:
            raise LookupError("session not found")
        await self._sync_runtime(row)
        src_row = await self._sources.get(UUID(row.source_id), organization_id)
        if not src_row:
            raise LookupError("source not found")
        rate_json = src_row.rate_limit_json or "{}"
        gated = parse_confirmation_gated_allowlist(rate_json)
        state = BrowserSessionState(row.status)
        if action_type not in gated:
            return {
                "lifecycle": BrowserActionLifecycle.BLOCKED.value,
                "summary": "Side-effect action not allowlisted for this source.",
                "policy_reason": "confirmation_action_not_allowlisted",
                "action_type": action_type.value,
            }
        if state not in (
            BrowserSessionState.RUNNING,
            BrowserSessionState.NEEDS_USER_ACTION,
        ):
            return {
                "lifecycle": BrowserActionLifecycle.BLOCKED.value,
                "summary": "Session is not actionable.",
                "policy_reason": "session_not_actionable",
                "action_type": action_type.value,
            }
        conf_repo = BrowserActionConfirmationRepository(self._session)
        pending = await conf_repo.get_pending_for_session(session_id, organization_id)
        if pending:
            return _confirmation_response(pending, row, src_row)
        if action_type == BrowserActionType.SUBMIT_FORM:
            norm, param_errors = normalize_submit_form_parameters(parameters)
        else:
            norm, param_errors = {}, ("unsupported_confirmation_action",)
        if param_errors:
            return {
                "lifecycle": BrowserActionLifecycle.FAILED.value,
                "summary": "Invalid action parameters.",
                "policy_reason": ",".join(param_errors),
                "action_type": action_type.value,
            }
        preview = build_action_preview(
            action_type=action_type,
            parameters=norm,
            session_url=row.current_url or row.initial_url,
            source_name=row.source_name or src_row.name,
        )
        expires = confirmation_expires_at()
        conf_row = await conf_repo.add(
            BrowserActionConfirmationRepository.new_row(
                session_id=session_id,
                organization_id=organization_id,
                requested_by=actor,
                action_type=action_type.value,
                parameters_json=json.dumps(norm),
                preview_json=json.dumps(preview),
                expires_at=expires,
            )
        )
        action_repo = BrowserSessionActionRepository(self._session)
        await action_repo.add(
            BrowserSessionActionRepository.new_row(
                session_id=session_id,
                organization_id=organization_id,
                actor=actor,
                action_type=action_type.value,
                parameters_json=json.dumps(norm),
                lifecycle=BrowserActionLifecycle.CONFIRMATION_REQUIRED.value,
                summary="Confirmation required before side-effect execution.",
                detail=conf_row.id,
            )
        )
        row.latest_action_summary = "Awaiting confirmation for side-effect action."
        await self._session.flush()
        logger.info(
            "browser_confirmation_required session=%s confirmation=%s type=%s actor=%s",
            session_id,
            conf_row.id,
            action_type.value,
            actor,
        )
        return _confirmation_response(conf_row, row, src_row)

    async def confirm_browser_action(
        self,
        confirmation_id: UUID,
        organization_id: UUID,
        actor: str,
    ) -> dict:
        conf_repo = BrowserActionConfirmationRepository(self._session)
        conf = await conf_repo.get(confirmation_id, organization_id)
        if not conf:
            raise LookupError("confirmation not found")
        session_id = UUID(conf.session_id)
        row = await self._repo.get(session_id, organization_id)
        if not row:
            raise LookupError("session not found")
        await self._sync_runtime(row)
        src_row = await self._sources.get(UUID(row.source_id), organization_id)
        if not src_row:
            raise LookupError("source not found")
        stored = BrowserConfirmationState(conf.state)
        decision = can_confirm(
            state=stored,
            expires_at=conf.expires_at,
            session_state=BrowserSessionState(row.status),
        )
        effective = effective_confirmation_state(stored, expires_at=conf.expires_at)
        if effective == BrowserConfirmationState.EXPIRED and conf.state == BrowserConfirmationState.PENDING.value:
            conf.state = BrowserConfirmationState.EXPIRED.value
            await self._session.flush()
        if not decision.allowed:
            return {
                "confirmation_id": conf.id,
                "confirmation_state": effective.value,
                "lifecycle": BrowserActionLifecycle.BLOCKED.value,
                "summary": "Cannot confirm this request.",
                "policy_reason": decision.reason,
                "action_type": conf.action_type,
            }
        from datetime import UTC, datetime

        conf.state = BrowserConfirmationState.CONFIRMED.value
        conf.confirmed_by = actor
        conf.confirmed_at = datetime.now(UTC)
        await self._session.flush()
        action_type = BrowserActionType(conf.action_type)
        norm = json.loads(conf.parameters_json or "{}")
        timeout_ms = action_timeout_ms(src_row.rate_limit_json)
        runtime_out = execute_confirmation_gated_action(
            session_id,
            action_type=action_type,
            parameters=norm,
            timeout_ms=timeout_ms,
            source_domain=row.source_domain or src_row.domain,
        )
        action_repo = BrowserSessionActionRepository(self._session)
        if runtime_out is None:
            conf.state = BrowserConfirmationState.BLOCKED.value
            conf.execution_summary = "No active browser runtime."
            await self._session.flush()
            return {
                "confirmation_id": conf.id,
                "confirmation_state": conf.state,
                "lifecycle": BrowserActionLifecycle.FAILED.value,
                "summary": "No active browser runtime for this session.",
                "action_type": conf.action_type,
            }
        lifecycle = str(runtime_out.get("lifecycle", "failed"))
        action_row = await action_repo.add(
            BrowserSessionActionRepository.new_row(
                session_id=session_id,
                organization_id=organization_id,
                actor=actor,
                action_type=conf.action_type,
                parameters_json=conf.parameters_json,
                lifecycle=lifecycle,
                summary=str(runtime_out.get("summary", "")),
                detail=runtime_out.get("detail"),
                policy_reason=runtime_out.get("policy_reason"),
            )
        )
        conf.state = BrowserConfirmationState.EXECUTED.value
        conf.executed_action_id = action_row.id
        conf.execution_lifecycle = lifecycle
        conf.execution_summary = str(runtime_out.get("summary", ""))
        await self._sync_runtime(row)
        logger.info(
            "browser_confirmation_executed confirmation=%s session=%s actor=%s lifecycle=%s",
            conf.id,
            session_id,
            actor,
            lifecycle,
        )
        return {
            "confirmation_id": conf.id,
            "confirmation_state": conf.state,
            "action_type": conf.action_type,
            "lifecycle": lifecycle,
            "summary": runtime_out.get("summary", ""),
            "detail": runtime_out.get("detail"),
            "policy_reason": runtime_out.get("policy_reason"),
            "current_url": runtime_out.get("current_url") or row.current_url,
        }

    async def cancel_browser_action(
        self,
        confirmation_id: UUID,
        organization_id: UUID,
        actor: str,
    ) -> dict:
        conf_repo = BrowserActionConfirmationRepository(self._session)
        conf = await conf_repo.get(confirmation_id, organization_id)
        if not conf:
            raise LookupError("confirmation not found")
        stored = BrowserConfirmationState(conf.state)
        decision = can_cancel(state=stored, expires_at=conf.expires_at)
        effective = effective_confirmation_state(stored, expires_at=conf.expires_at)
        if effective == BrowserConfirmationState.EXPIRED and conf.state == BrowserConfirmationState.PENDING.value:
            conf.state = BrowserConfirmationState.EXPIRED.value
            await self._session.flush()
        if not decision.allowed:
            return {
                "confirmation_id": conf.id,
                "confirmation_state": effective.value,
                "lifecycle": BrowserActionLifecycle.BLOCKED.value,
                "summary": "Cannot cancel this request.",
                "policy_reason": decision.reason,
                "action_type": conf.action_type,
            }
        from datetime import UTC, datetime

        conf.state = BrowserConfirmationState.CANCELLED.value
        conf.cancelled_by = actor
        conf.cancelled_at = datetime.now(UTC)
        action_repo = BrowserSessionActionRepository(self._session)
        await action_repo.add(
            BrowserSessionActionRepository.new_row(
                session_id=UUID(conf.session_id),
                organization_id=organization_id,
                actor=actor,
                action_type=conf.action_type,
                parameters_json=conf.parameters_json,
                lifecycle=BrowserActionLifecycle.CANCELLED.value,
                summary="Side-effect action cancelled by user.",
                detail=conf.id,
            )
        )
        row = await self._repo.get(UUID(conf.session_id), organization_id)
        if row:
            row.latest_action_summary = "Side-effect action cancelled."
            await self._session.flush()
        logger.info(
            "browser_confirmation_cancelled confirmation=%s actor=%s",
            conf.id,
            actor,
        )
        return {
            "confirmation_id": conf.id,
            "confirmation_state": conf.state,
            "action_type": conf.action_type,
            "lifecycle": BrowserActionLifecycle.CANCELLED.value,
            "summary": "Side-effect action cancelled.",
        }

    async def execute_action(
        self,
        session_id: UUID,
        organization_id: UUID,
        actor: str,
        *,
        action_type: BrowserActionType,
        parameters: dict,
    ) -> dict:
        if requires_confirmation(action_type):
            return await self.request_confirmation_gated_action(
                session_id,
                organization_id,
                actor,
                action_type=action_type,
                parameters=parameters,
            )
        row = await self._repo.get(session_id, organization_id)
        if not row:
            raise LookupError("session not found")
        await self._sync_runtime(row)
        src_row = await self._sources.get(UUID(row.source_id), organization_id)
        if not src_row:
            raise LookupError("source not found")
        rate_json = src_row.rate_limit_json or "{}"
        allowlist = parse_browser_action_allowlist(rate_json)
        max_actions = max_actions_per_session(rate_json)
        timeout_ms = action_timeout_ms(rate_json)
        action_repo = BrowserSessionActionRepository(self._session)
        used = await action_repo.count_for_session(session_id)
        state = BrowserSessionState(row.status)
        decision = evaluate_action_policy_with_json(
            allowlist=allowlist,
            session_state=state,
            action_type=action_type,
            actions_used=used,
            max_actions=max_actions,
        )
        if not decision.allowed:
            reason = ",".join(decision.reasons)
            await action_repo.add(
                BrowserSessionActionRepository.new_row(
                    session_id=session_id,
                    organization_id=organization_id,
                    actor=actor,
                    action_type=action_type.value,
                    parameters_json=json.dumps(parameters),
                    lifecycle=BrowserActionLifecycle.BLOCKED.value,
                    summary="Action blocked by policy.",
                    policy_reason=reason,
                )
            )
            logger.info(
                "browser_action_blocked session=%s type=%s reasons=%s",
                session_id,
                action_type.value,
                reason,
            )
            return {
                "action_type": action_type.value,
                "lifecycle": BrowserActionLifecycle.BLOCKED.value,
                "summary": "Action blocked by policy.",
                "policy_reason": reason,
            }

        norm, param_errors = normalize_action_parameters(action_type, parameters)
        if param_errors:
            await action_repo.add(
                BrowserSessionActionRepository.new_row(
                    session_id=session_id,
                    organization_id=organization_id,
                    actor=actor,
                    action_type=action_type.value,
                    parameters_json=json.dumps(parameters),
                    lifecycle=BrowserActionLifecycle.FAILED.value,
                    summary="Invalid action parameters.",
                    policy_reason=",".join(param_errors),
                )
            )
            return {
                "action_type": action_type.value,
                "lifecycle": BrowserActionLifecycle.FAILED.value,
                "summary": "Invalid action parameters.",
                "policy_reason": ",".join(param_errors),
            }

        runtime_out = execute_read_only_action(
            session_id,
            action_type=action_type,
            parameters=norm,
            timeout_ms=timeout_ms,
            source_domain=row.source_domain or src_row.domain,
        )
        if runtime_out is None:
            summary = "No active browser runtime for this session."
            detail = "Session may have ended or the worker process restarted. Open a new browser session from the event."
            await action_repo.add(
                BrowserSessionActionRepository.new_row(
                    session_id=session_id,
                    organization_id=organization_id,
                    actor=actor,
                    action_type=action_type.value,
                    parameters_json=json.dumps(norm),
                    lifecycle=BrowserActionLifecycle.FAILED.value,
                    summary=summary,
                    detail=detail,
                )
            )
            return {
                "action_type": action_type.value,
                "lifecycle": BrowserActionLifecycle.FAILED.value,
                "summary": summary,
                "detail": detail,
            }

        lifecycle = str(runtime_out.get("lifecycle", "failed"))
        await action_repo.add(
            BrowserSessionActionRepository.new_row(
                session_id=session_id,
                organization_id=organization_id,
                actor=actor,
                action_type=action_type.value,
                parameters_json=json.dumps(norm),
                lifecycle=lifecycle,
                summary=str(runtime_out.get("summary", "")),
                detail=runtime_out.get("detail"),
                policy_reason=runtime_out.get("policy_reason"),
            )
        )
        await self._sync_runtime(row)
        logger.info(
            "browser_action_done session=%s type=%s lifecycle=%s actor=%s",
            session_id,
            action_type.value,
            lifecycle,
            actor,
        )
        payload = {
            "action_type": action_type.value,
            "lifecycle": lifecycle,
            "summary": runtime_out.get("summary", ""),
            "detail": runtime_out.get("detail"),
            "policy_reason": runtime_out.get("policy_reason"),
            "current_url": runtime_out.get("current_url") or row.current_url,
        }
        if runtime_out.get("text_preview"):
            payload["text_preview"] = runtime_out["text_preview"]
        return payload

    async def _sync_runtime(self, row) -> None:
        runtime = read_runtime(UUID(row.id))
        if not runtime:
            return
        await self._apply_runtime_dict(row, runtime)

    async def _apply_runtime_dict(self, row, runtime: dict) -> None:
        state = runtime["state"]
        if isinstance(state, BrowserSessionState):
            status = state.value
        else:
            status = str(state.value if hasattr(state, "value") else state)
        row.status = status
        row.current_url = runtime.get("current_url") or row.current_url
        row.latest_action_summary = (
            runtime.get("latest_action_summary") or row.latest_action_summary
        )
        if runtime.get("started_at"):
            row.started_at = runtime["started_at"]
        if runtime.get("ended_at"):
            row.ended_at = runtime["ended_at"]
        if runtime.get("worker_id"):
            row.worker_id = runtime["worker_id"]
        if runtime.get("stop_requested") is not None:
            row.stop_requested = bool(runtime["stop_requested"])
        if runtime.get("error_summary") is not None:
            row.error_summary = runtime["error_summary"]
        await self._session.flush()


def _confirmation_response(conf, row, src_row) -> dict:
    preview = json.loads(conf.preview_json or "{}")
    effective = effective_confirmation_state(
        BrowserConfirmationState(conf.state),
        expires_at=conf.expires_at,
    )
    return {
        "action_type": conf.action_type,
        "lifecycle": BrowserActionLifecycle.CONFIRMATION_REQUIRED.value,
        "summary": "Review the preview and confirm or cancel this side-effect action.",
        "confirmation_id": conf.id,
        "confirmation_state": effective.value,
        "preview": preview,
        "expires_at": conf.expires_at.isoformat(),
        "current_url": row.current_url or row.initial_url,
        "requested_by": conf.requested_by,
    }


def session_status_view(record: BrowserSessionRecord) -> dict:
    return {
        "id": str(record.id),
        "state": record.state.value,
        "engine": record.engine.value,
        "current_url": record.current_url,
        "runtime_seconds": runtime_seconds(
            started_at=record.started_at,
            ended_at=record.ended_at,
        ),
        "latest_action_summary": record.latest_action_summary,
        "isolation": {
            "isolation_key": record.isolation.isolation_key,
            "profile_boundary": record.isolation.profile_boundary,
        },
        "target": {
            "kind": record.target.kind.value,
            "event_id": str(record.target.event_id) if record.target.event_id else None,
            "source_id": str(record.target.source_id),
            "source_name": record.target.source_name,
            "source_domain": record.target.source_domain,
            "initial_url": record.target.initial_url,
        },
        "stop_requested": record.stop_requested,
        "terminal": is_terminal(record.state),
        "error_summary": record.error_summary,
        "started_at": record.started_at.isoformat() if record.started_at else None,
        "ended_at": record.ended_at.isoformat() if record.ended_at else None,
        "created_at": record.created_at.isoformat(),
        "debug_enabled": record.debug_enabled,
        "latest_artifact_summary": record.latest_artifact_summary,
    }
