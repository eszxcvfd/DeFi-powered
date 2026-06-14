"""Synchronous scoring for worker after event normalization."""

import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from livelead.domain.scoring.calculator import ScoreResult, calculate_event_score
from livelead.infrastructure.db.event_mappers import row_to_event, score_result_to_json_payload
from livelead.infrastructure.db.mappers import row_to_campaign
from livelead.infrastructure.db.models import Base, CampaignRow, EventRow, EventScoreRow
from livelead.runtime.settings import parse_settings

logger = logging.getLogger("livelead.scoring")


def _sync_session() -> Session:
    settings = parse_settings()
    url = settings.database_url.replace("sqlite+aiosqlite", "sqlite")
    engine = create_engine(url, echo=False)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _append_score_sync(
    session: Session, event_id: UUID, campaign_id: UUID, result: ScoreResult
) -> None:
    now = datetime.now(UTC)
    existing = session.execute(
        select(EventScoreRow).where(
            EventScoreRow.event_id == str(event_id),
            EventScoreRow.campaign_id == str(campaign_id),
            EventScoreRow.superseded_at.is_(None),
        )
    )
    for old in existing.scalars().all():
        old.superseded_at = now
        session.add(old)
    w_json, c_json, e_json = score_result_to_json_payload(result)
    session.add(
        EventScoreRow(
            id=str(uuid4()),
            event_id=str(event_id),
            campaign_id=str(campaign_id),
            total_score=result.total_score,
            priority_level=result.priority_level.value,
            scoring_version=result.scoring_version,
            calculated_at=now,
            weights_snapshot_json=w_json,
            components_json=c_json,
            explanation_json=e_json,
            superseded_at=None,
        )
    )


def score_all_for_campaign_sync(campaign_id: str, organization_id: str) -> int:
    session = _sync_session()
    count = 0
    try:
        camp_row = session.execute(
            select(CampaignRow).where(
                CampaignRow.id == campaign_id,
                CampaignRow.organization_id == organization_id,
            )
        ).scalar_one_or_none()
        if not camp_row:
            return 0
        campaign = row_to_campaign(camp_row)
        events = (
            session.execute(
                select(EventRow).where(
                    EventRow.campaign_id == campaign_id,
                    EventRow.organization_id == organization_id,
                )
            )
            .scalars()
            .all()
        )
        for erow in events:
            eid = UUID(erow.id)
            cid = UUID(campaign_id)
            has = session.execute(
                select(EventScoreRow.id).where(
                    EventScoreRow.event_id == erow.id,
                    EventScoreRow.campaign_id == campaign_id,
                    EventScoreRow.superseded_at.is_(None),
                )
            ).scalar_one_or_none()
            if has:
                continue
            event = row_to_event(erow)
            result = calculate_event_score(event, campaign)
            _append_score_sync(session, eid, cid, result)
            count += 1
        session.commit()
    finally:
        session.close()
    logger.info("campaign_events_scored campaign_id=%s count=%s", campaign_id, count)
    return count
