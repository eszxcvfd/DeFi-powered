"""Event watchlist application service (US-030).

The service layer owns:

- Idempotent watch / unwatch of a canonical event for the current
  user.
- Reminder create, change, and clear behavior.
- Projection of the current-user watch state into event list and
  event detail payloads.
- A durable history row for governance and a structured log line
  per mutation.
- A small ``evaluate_reminder_eligibility`` helper that future
  notification workflows can use to decide whether a watchlist
  reminder is eligible for delivery.

The service never mutates the canonical event, its source
observations, or any related lead. Removing a watch entry only
touches the watchlist tables.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audit.audit_service import (
    AuditService,
    make_actor_from_role,
    make_context,
)
from livelead.domain.audit.enums import (
    AuditAction,
    AuditActorType,
    AuditOutcome,
    AuditTargetType,
)
from livelead.domain.audit.model import AuditTarget
from livelead.domain.event_watchlist.models import (
    EventWatchState,
    EventWatchlistEntry,
    EventWatchlistHistoryEntry,
    WatchedEventListItem,
    WatchlistAction,
    WatchlistReminderStatus,
    classify_reminder_status,
    parse_reminder_at,
    serialize_reminder_at,
)
from livelead.infrastructure.db.repositories.event_watchlist import (
    EventWatchlistHistoryRepository,
    EventWatchlistRepository,
)

logger = logging.getLogger("livelead.event_watchlist")


class WatchlistValidationError(ValueError):
    """Raised for caller-facing validation failures.

    Routes convert this to a 400 response. The message is safe to
    surface to the user because it only describes the rejected
    input shape.
    """


@dataclass(frozen=True, slots=True)
class WatchlistUpsertResult:
    entry: EventWatchlistEntry
    history: EventWatchlistHistoryEntry
    created: bool


@dataclass(frozen=True, slots=True)
class WatchlistRemovalResult:
    removed: bool
    history: EventWatchlistHistoryEntry | None


@dataclass(frozen=True, slots=True)
class ReminderEligibility:
    """Future-facing eligibility signal for watchlist reminder alerts.

    The notification service can consume this dataclass to decide
    whether a watched event is eligible for an upcoming reminder
    without re-deriving the rules in another module. The fields are
    intentionally narrow so callers cannot accidentally treat the
    watch entry as an unrelated record.
    """

    entry_id: UUID
    event_id: UUID
    user_id: UUID
    organization_id: UUID
    reminder_at: datetime
    status: WatchlistReminderStatus
    title: str = ""
    deep_link: str = ""


class EventWatchlistService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = EventWatchlistRepository(session)
        self._history = EventWatchlistHistoryRepository(session)
        self._audit = AuditService(session)

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------
    async def upsert(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        actor_id: str,
        actor_role: str,
        event_id: UUID,
        reminder_at_raw: str | None,
        reminder_note: str = "",
        request_id: str = "",
    ) -> WatchlistUpsertResult:
        try:
            reminder_at = parse_reminder_at(reminder_at_raw)
        except ValueError as exc:
            raise WatchlistValidationError(
                "reminder_at must be an ISO-8601 timestamp or null"
            ) from exc
        note = (reminder_note or "").strip()[:500]

        previous = await self._repo.get_entry(organization_id, user_id, event_id)
        entry = await self._repo.upsert_entry(
            organization_id=organization_id,
            user_id=user_id,
            event_id=event_id,
            reminder_at=reminder_at,
            reminder_note=note,
            actor_id=actor_id,
            actor_role=actor_role,
        )
        action = self._classify_upsert_action(previous, entry)
        history = await self._history.append(
            organization_id=organization_id,
            user_id=user_id,
            event_id=event_id,
            entry_id=entry.id,
            action=action,
            actor_id=actor_id,
            actor_role=actor_role,
            from_reminder_at=serialize_reminder_at(previous.reminder_at) if previous else None,
            to_reminder_at=serialize_reminder_at(entry.reminder_at),
            note=note,
        )
        await self._emit_audit(
            action=AuditAction.WATCHLIST_UPSERTED,
            organization_id=organization_id,
            actor_id=actor_id,
            actor_role=actor_role,
            event_id=event_id,
            entry_id=entry.id,
            outcome=AuditOutcome.SUCCEEDED,
            request_id=request_id,
            metadata={
                "watchlist_action": action.value,
                "reminder_at": entry.reminder_at.isoformat() if entry.reminder_at else None,
            },
        )
        logger.info(
            "watchlist_upsert org=%s user=%s event=%s action=%s entry=%s",
            organization_id,
            user_id,
            event_id,
            action.value,
            entry.id,
        )
        return WatchlistUpsertResult(
            entry=entry,
            history=history,
            created=previous is None,
        )

    async def remove(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        actor_id: str,
        actor_role: str,
        event_id: UUID,
        request_id: str = "",
        note: str = "",
    ) -> WatchlistRemovalResult:
        previous = await self._repo.get_entry(organization_id, user_id, event_id)
        if previous is None:
            return WatchlistRemovalResult(removed=False, history=None)
        removed = await self._repo.delete_entry(organization_id, user_id, event_id)
        if not removed:
            return WatchlistRemovalResult(removed=False, history=None)
        history = await self._history.append(
            organization_id=organization_id,
            user_id=user_id,
            event_id=event_id,
            entry_id=None,
            action=WatchlistAction.UNWATCHED,
            actor_id=actor_id,
            actor_role=actor_role,
            from_reminder_at=serialize_reminder_at(previous.reminder_at),
            to_reminder_at=None,
            note=(note or "").strip()[:500],
        )
        await self._emit_audit(
            action=AuditAction.WATCHLIST_REMOVED,
            organization_id=organization_id,
            actor_id=actor_id,
            actor_role=actor_role,
            event_id=event_id,
            entry_id=previous.id,
            outcome=AuditOutcome.SUCCEEDED,
            request_id=request_id,
            metadata={
                "watchlist_action": WatchlistAction.UNWATCHED.value,
                "had_reminder": previous.reminder_at is not None,
            },
        )
        logger.info(
            "watchlist_remove org=%s user=%s event=%s entry=%s",
            organization_id,
            user_id,
            event_id,
            previous.id,
        )
        return WatchlistRemovalResult(removed=True, history=history)

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------
    async def list_for_user(
        self,
        organization_id: UUID,
        user_id: UUID,
        *,
        has_reminder: bool | None = None,
        limit: int = 100,
    ) -> list[WatchedEventListItem]:
        return await self._repo.list_for_user(
            organization_id,
            user_id,
            has_reminder=has_reminder,
            limit=limit,
        )

    async def project_state(
        self,
        organization_id: UUID,
        user_id: UUID,
        event_ids: Iterable[UUID],
    ) -> dict[UUID, EventWatchState]:
        ids = list(event_ids)
        if not ids:
            return {}
        entries = await self._repo.list_projection_for_events(
            organization_id, user_id, ids
        )
        out: dict[UUID, EventWatchState] = {}
        for event_id in ids:
            entry = entries.get(event_id)
            out[event_id] = self._state_for(event_id, entry)
        return out

    async def get_state(
        self,
        organization_id: UUID,
        user_id: UUID,
        event_id: UUID,
    ) -> EventWatchState:
        entry = await self._repo.get_entry(organization_id, user_id, event_id)
        return self._state_for(event_id, entry)

    # ------------------------------------------------------------------
    # Future notification handoff
    # ------------------------------------------------------------------
    async def evaluate_reminder_eligibility(
        self,
        organization_id: UUID,
        *,
        now: datetime | None = None,
    ) -> list[ReminderEligibility]:
        """Return every entry whose reminder timestamp is at or before ``now``.

        The notification slice can pull this list to drive reminder
        delivery without re-implementing the eligibility rules. The
        eligibility surface never mutates the watchlist.
        """

        entries = await self._repo.list_open_reminders(organization_id, now=now)
        out: list[ReminderEligibility] = []
        for entry in entries:
            if entry.reminder_at is None:
                continue
            status = entry.reminder_status(now=now)
            out.append(
                ReminderEligibility(
                    entry_id=entry.id,
                    event_id=entry.event_id,
                    user_id=entry.user_id,
                    organization_id=entry.organization_id,
                    reminder_at=entry.reminder_at,
                    status=status,
                )
            )
        return out

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _state_for(
        self, event_id: UUID, entry: EventWatchlistEntry | None
    ) -> EventWatchState:
        if entry is None:
            return EventWatchState.not_watched(event_id)
        reminder_at = (
            entry.reminder_at.isoformat().replace("+00:00", "Z")
            if entry.reminder_at
            else None
        )
        status = classify_reminder_status(entry.reminder_at)
        return EventWatchState(
            event_id=event_id,
            is_watched=True,
            watchlist_entry_id=entry.id,
            reminder_at=reminder_at,
            reminder_status=status,
            reminder_note=entry.reminder_note,
            last_action_at=(
                entry.last_action_at.isoformat().replace("+00:00", "Z")
                if entry.last_action_at
                else None
            ),
            reminder_eligible=status == WatchlistReminderStatus.OVERDUE
            or entry.reminder_at is not None,
        )

    def _classify_upsert_action(
        self,
        previous: EventWatchlistEntry | None,
        current: EventWatchlistEntry,
    ) -> WatchlistAction:
        if previous is None:
            return (
                WatchlistAction.REMINDER_SET
                if current.reminder_at is not None
                else WatchlistAction.WATCHED
            )
        if previous.reminder_at == current.reminder_at:
            return WatchlistAction.WATCHED
        if current.reminder_at is None:
            return WatchlistAction.REMINDER_CLEARED
        if previous.reminder_at is None:
            return WatchlistAction.REMINDER_SET
        return WatchlistAction.REMINDER_CHANGED

    async def _emit_audit(
        self,
        *,
        action: AuditAction,
        organization_id: UUID,
        actor_id: str,
        actor_role: str,
        event_id: UUID,
        entry_id: UUID,
        outcome: AuditOutcome,
        request_id: str,
        metadata: dict,
    ) -> None:
        try:
            target = AuditTarget(
                target_type=AuditTargetType.WATCHLIST_ENTRY,
                target_id=str(entry_id),
                display=f"event {event_id}",
            )
            await self._audit.emit(
                organization_id=organization_id,
                actor=make_actor_from_role(actor_role, actor_id or actor_role),
                action=action,
                target=target,
                outcome=outcome,
                context=make_context(
                    request_id=request_id,
                    workflow="event_watchlist",
                ),
                metadata=metadata,
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("watchlist_audit_failed err=%s", exc)


__all__ = [
    "EventWatchlistService",
    "ReminderEligibility",
    "WatchlistRemovalResult",
    "WatchlistUpsertResult",
    "WatchlistValidationError",
]
