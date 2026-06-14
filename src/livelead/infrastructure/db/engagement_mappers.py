import json
from uuid import UUID

from livelead.domain.engagement.models import (
    EngagementPhase,
    EngagementPlan,
    EngagementTask,
    EngagementTaskStatus,
)
from livelead.infrastructure.db.models import EngagementPlanRow, EngagementTaskRow


def row_to_plan(row: EngagementPlanRow) -> EngagementPlan:
    notes = json.loads(row.generation_notes_json or "[]")
    return EngagementPlan(
        id=UUID(row.id),
        event_id=UUID(row.event_id),
        campaign_id=UUID(row.campaign_id),
        strategy_version=row.strategy_version,
        generation_notes=tuple(n for n in notes if isinstance(n, str)),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def row_to_task(row: EngagementTaskRow) -> EngagementTask:
    return EngagementTask(
        id=UUID(row.id),
        plan_id=UUID(row.plan_id),
        event_id=UUID(row.event_id),
        phase=EngagementPhase(row.phase),
        title=row.title,
        rationale=row.rationale,
        status=EngagementTaskStatus(row.status),
        assignee=row.assignee or "",
        deadline=row.deadline,
        notes=row.notes or "",
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def notes_to_json(notes: tuple[str, ...]) -> str:
    return json.dumps(list(notes))