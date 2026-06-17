"""Mappers for the lead CSV import/export tables (US-050)."""

from __future__ import annotations

import json
from uuid import UUID

from livelead.domain.leads.import_export import (
    LeadImportClassification,
    LeadImportJob,
    LeadImportRow,
    LeadImportStatus,
)
from livelead.infrastructure.db.models import LeadImportJobRow, LeadImportRowRow


def _loads(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _loads_list(raw: str | None) -> list:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return data if isinstance(data, list) else []


def row_to_import_job(row: LeadImportJobRow) -> LeadImportJob:
    return LeadImportJob(
        id=UUID(row.id),
        organization_id=UUID(row.organization_id),
        created_by_user_id=row.created_by_user_id or "system",
        actor_role=row.actor_role or "viewer",
        filename=row.filename,
        file_sha256=row.file_sha256,
        delimiter=row.delimiter or ",",
        mapping=_loads(row.mapping_json),
        provenance_note=row.provenance_note or "",
        campaign_id=UUID(row.campaign_id) if row.campaign_id else None,
        status=LeadImportStatus(row.status) if row.status else LeadImportStatus.PREVIEWED,
        total_rows=int(row.total_rows or 0),
        ready_rows=int(row.ready_rows or 0),
        duplicate_rows=int(row.duplicate_rows or 0),
        invalid_rows=int(row.invalid_rows or 0),
        created_rows=int(row.created_rows or 0),
        skipped_rows=int(row.skipped_rows or 0),
        error_message=row.error_message or "",
        created_at=row.created_at.isoformat() if row.created_at else "",
        applied_at=row.applied_at.isoformat() if row.applied_at else None,
    )


def row_to_import_row(row: LeadImportRowRow) -> LeadImportRow:
    classification_value = row.classification or LeadImportClassification.INVALID.value
    return LeadImportRow(
        id=UUID(row.id),
        import_job_id=UUID(row.import_job_id),
        organization_id=UUID(row.organization_id),
        row_number=int(row.row_number or 0),
        normalized=_loads(row.normalized_payload_json),
        classification=LeadImportClassification(classification_value),
        duplicate_lead_id=UUID(row.duplicate_lead_id) if row.duplicate_lead_id else None,
        duplicate_reason=row.duplicate_reason or "",
        error_codes=tuple(_loads_list(row.error_codes_json)),
        created_lead_id=UUID(row.created_lead_id) if row.created_lead_id else None,
        created_at=row.created_at.isoformat() if row.created_at else "",
        updated_at=row.updated_at.isoformat() if row.updated_at else "",
    )


__all__ = ["row_to_import_job", "row_to_import_row"]
