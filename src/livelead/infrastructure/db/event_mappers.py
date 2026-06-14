"""Map event ORM rows to domain."""

import json
from uuid import UUID

from livelead.domain.events.models import CanonicalEvent, EventSourceObservation
from livelead.domain.scoring.models import (
    EventScore,
    PriorityLevel,
    ScoreComponent,
    ScoreExplanation,
)
from livelead.infrastructure.db.models import EventRow, EventScoreRow, EventSourceObservationRow


def row_to_event(row: EventRow) -> CanonicalEvent:
    meta = json.loads(row.metadata_json or "{}")
    simple_meta = {
        k: (json.dumps(v) if isinstance(v, (list, dict)) else str(v))
        for k, v in meta.items()
        if k not in ("field_confidence", "merge_notes")
    }
    return CanonicalEvent(
        id=UUID(row.id),
        organization_id=UUID(row.organization_id),
        campaign_id=UUID(row.campaign_id),
        canonical_title=row.canonical_title,
        source_url=row.source_url,
        observed_at=row.observed_at,
        description=row.description or "",
        organizer=row.organizer or "",
        region=row.region or "",
        starts_at=row.starts_at,
        metadata_json=simple_meta,
        discovery_job_id=row.discovery_job_id,
        confidence_summary=str(meta.get("confidence_summary", "medium")),
        created_at=row.created_at,
    )


def row_to_observation(row: EventSourceObservationRow) -> EventSourceObservation:
    return EventSourceObservation(
        id=UUID(row.id),
        event_id=UUID(row.event_id),
        source_id=UUID(row.source_id),
        source_url=row.source_url,
        observed_at=row.observed_at,
        raw_title=row.raw_title or "",
        external_id=row.external_id,
        discovery_job_id=row.discovery_job_id,
    )


def row_to_score(row: EventScoreRow) -> EventScore:
    comps_raw = json.loads(row.components_json or "[]")
    expl_raw = json.loads(row.explanation_json or "{}")
    weights = json.loads(row.weights_snapshot_json or "{}")
    components = tuple(
        ScoreComponent(
            key=c["key"],
            raw_value=float(c["raw_value"]),
            weighted_contribution=float(c["weighted_contribution"]),
            evidence=c.get("evidence", ""),
            missing_data=list(c.get("missing_data", [])),
        )
        for c in comps_raw
    )
    explanation = ScoreExplanation(
        components=components,
        missing_fields=tuple(expl_raw.get("missing_fields", [])),
        score_reducers=tuple(expl_raw.get("score_reducers", [])),
    )
    return EventScore(
        id=UUID(row.id),
        event_id=UUID(row.event_id),
        campaign_id=UUID(row.campaign_id),
        total_score=float(row.total_score),
        priority_level=PriorityLevel(row.priority_level),
        scoring_version=row.scoring_version,
        calculated_at=row.calculated_at,
        weights_snapshot={k: float(v) for k, v in weights.items()},
        components=components,
        explanation=explanation,
    )


def score_result_to_json_payload(result) -> tuple[str, str, str]:
    from livelead.domain.scoring.calculator import ScoreResult

    assert isinstance(result, ScoreResult)
    comps = [
        {
            "key": c.key,
            "raw_value": c.raw_value,
            "weighted_contribution": c.weighted_contribution,
            "evidence": c.evidence,
            "missing_data": c.missing_data,
        }
        for c in result.components
    ]
    expl = {
        "missing_fields": list(result.explanation.missing_fields),
        "score_reducers": list(result.explanation.score_reducers),
    }
    return (
        json.dumps(result.weights_snapshot),
        json.dumps(comps),
        json.dumps(expl),
    )
