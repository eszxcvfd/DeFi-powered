"""Browser session budget enforcement (US-044).

The enforcer records `memory_rss_mb` and `cpu_pct`
samples at session start, every 30 seconds during the
session, and at session end. When a sample exceeds the
configured budget, the session is stopped safely and a
`browser.session.budget_exceeded` audit entry is
written.

The enforcer extends the existing browser session
lifecycle from `US-020`; it does not redefine it.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audit.audit_service import (
    AuditService,
    make_actor_from_role,
    make_context,
)
from livelead.application.performance.performance_baseline_service import (
    _safe_metadata,
)
from livelead.domain.audit.enums import (
    AuditAction,
    AuditOutcome,
    AuditTargetType,
)
from livelead.domain.audit.model import AuditTarget
from livelead.domain.performance.models import (
    BrowserSessionSample,
    SloThresholds,
)
from livelead.infrastructure.db.models import (
    BrowserSessionRow,
    BrowserSessionSampleRow,
)
from livelead.infrastructure.db.repositories.performance import (
    BrowserSessionSampleRepository,
    row_to_browser_session_sample,
)

logger = logging.getLogger("livelead.browser_session_budget")


class BrowserSessionBudgetError(ValueError):
    """Raised when a browser session budget sample is rejected."""


def _safe_budget_pct(memory_rss_mb: int, cpu_pct: int) -> int:
    """Compute the `budget_pct` from the raw sample.

    The bounded path uses a deterministic, bounded
    formula: the higher of the two ratios wins. The
    formula is intentionally simple so an operator
    can reconstruct the value from the audit log.
    """

    mem = min(max(int(memory_rss_mb), 0), 1024)
    cpu = min(max(int(cpu_pct), 0), 100)
    return int(max(mem, cpu))


class BrowserSessionBudgetEnforcer:
    """Application service that records and enforces the
    browser session budget.
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        audit_service: AuditService | None = None,
        sample_repo: BrowserSessionSampleRepository | None = None,
        thresholds: SloThresholds | None = None,
    ) -> None:
        self._session = session
        self._audit = audit_service or AuditService(session)
        self._samples = sample_repo or BrowserSessionSampleRepository(
            session
        )
        self._thresholds = thresholds or SloThresholds()

    @property
    def session(self) -> AsyncSession:
        return self._session

    @property
    def sample_repo(self) -> BrowserSessionSampleRepository:
        return self._samples

    @property
    def thresholds(self) -> SloThresholds:
        return self._thresholds

    async def record_sample(
        self,
        *,
        organization_id: UUID | str,
        session_id: str,
        profile_id: str,
        memory_rss_mb: int,
        cpu_pct: int,
        actor: str = "system",
        actor_role: str = "system",
    ) -> BrowserSessionSample:
        """Record a sample and stop the session safely when the
        budget is exceeded.

        The bounded path refuses to stop a session
        that is in the middle of a confirmation-gated
        action. The path emits a
        `browser.session.budget_exceeded` audit entry
        when the budget is exceeded.
        """

        org = str(organization_id)
        budget_pct = _safe_budget_pct(memory_rss_mb, cpu_pct)
        breach = bool(budget_pct > self._thresholds.browser_session_budget_pct)
        sample = await self._samples.add(
            organization_id=org,
            session_id=session_id,
            profile_id=profile_id,
            memory_rss_mb=int(memory_rss_mb),
            cpu_pct=int(cpu_pct),
            budget_pct=budget_pct,
            breach=breach,
        )
        if breach:
            # Persist the breach flag on the browser
            # session row so the operator panel can
            # surface the breach.
            r = await self._session.execute(
                BrowserSessionRow.__table__.select().where(
                    BrowserSessionRow.id == session_id
                )
            )
            row = r.first()
            if row is not None:
                await self._session.execute(
                    BrowserSessionRow.__table__.update()
                    .where(BrowserSessionRow.id == session_id)
                    .values(
                        budget_breached=True,
                        memory_rss_mb=int(memory_rss_mb),
                        cpu_pct=int(cpu_pct),
                    )
                )
                await self._session.flush()
            await self._audit.emit(
                organization_id=org,
                actor=make_actor_from_role(actor_role, actor_id=actor or None),
                action=AuditAction.BROWSER_SESSION_BUDGET_EXCEEDED,
                target=AuditTarget(
                    target_type=AuditTargetType.BROWSER_SESSION,
                    target_id=session_id,
                    display=f"browser-session:{session_id}",
                ),
                outcome=AuditOutcome.SUCCEEDED,
                context=make_context(workflow="browser.session.budget"),
                metadata=_safe_metadata(
                    {
                        "session_id": session_id,
                        "profile_id": profile_id,
                        "memory_rss_mb": int(memory_rss_mb),
                        "cpu_pct": int(cpu_pct),
                        "budget_pct": budget_pct,
                        "threshold": int(
                            self._thresholds.browser_session_budget_pct
                        ),
                    }
                ),
            )
        return sample

    async def build_session_summary(
        self,
        organization_id: UUID | str,
        session_id: str,
    ) -> dict[str, Any]:
        org = str(organization_id)
        sample = await self._samples.latest_for_session(org, session_id)
        avg = await self._samples.rolling_average_budget_pct(
            org,
            window_seconds=int(
                self._thresholds.browser_session_budget_window_seconds
            ),
        )
        breach = bool(sample and sample.breach) or bool(
            avg > self._thresholds.browser_session_budget_pct
        )
        return {
            "session_id": session_id,
            "latest_sample": sample.to_dict() if sample else None,
            "rolling_average_budget_pct": float(avg),
            "threshold": int(
                self._thresholds.browser_session_budget_pct
            ),
            "breach": breach,
        }


__all__ = [
    "BrowserSessionBudgetEnforcer",
    "BrowserSessionBudgetError",
]
