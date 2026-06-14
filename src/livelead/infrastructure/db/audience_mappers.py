import json
from uuid import UUID

from livelead.domain.audience.models import (
    AudienceEvidenceItem,
    AudienceHypothesis,
    EvidenceKind,
    FitType,
)
from livelead.infrastructure.db.models import AudienceHypothesisRow


def row_to_hypothesis(row: AudienceHypothesisRow) -> AudienceHypothesis:
    raw = json.loads(row.evidence_json or "[]")
    evidence = tuple(
        AudienceEvidenceItem(
            cue=item["cue"],
            kind=EvidenceKind(item["kind"]),
            detail=item["detail"],
            source_field=item.get("source_field", ""),
        )
        for item in raw
        if isinstance(item, dict)
    )
    return AudienceHypothesis(
        id=UUID(row.id),
        event_id=UUID(row.event_id),
        segment_name=row.segment_name,
        fit_type=FitType(row.fit_type),
        reason=row.reason,
        confidence=float(row.confidence),
        generated_by=row.generated_by,
        model_version=row.model_version,
        evidence=evidence,
        created_at=row.created_at,
    )


def hypothesis_to_evidence_json(h: AudienceHypothesis) -> str:
    return json.dumps(
        [
            {
                "cue": e.cue,
                "kind": e.kind.value,
                "detail": e.detail,
                "source_field": e.source_field,
            }
            for e in h.evidence
        ]
    )