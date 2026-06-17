"""Integration tests for the backup and restore admin API (US-043)."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest


def _owner_headers() -> dict[str, str]:
    return {
        "X-Organization-Id": "00000000-0000-4000-8000-000000000001",
        "X-Actor-Role": "owner",
    }


def _admin_headers() -> dict[str, str]:
    return {
        "X-Organization-Id": "00000000-0000-4000-8000-000000000001",
        "X-Actor-Role": "admin",
    }


def _analyst_headers() -> dict[str, str]:
    return {
        "X-Organization-Id": "00000000-0000-4000-8000-000000000001",
        "X-Actor-Role": "analyst",
    }


def _viewer_headers() -> dict[str, str]:
    return {
        "X-Organization-Id": "00000000-0000-4000-8000-000000000001",
        "X-Actor-Role": "viewer",
    }


def _seed_backup_file(tmp_path: Path) -> str:
    """Create a fresh SQLite file on disk and return its path."""

    db_path = tmp_path / f"seed_{uuid4().hex[:8]}.sqlite3"
    db_path.write_bytes(b"seed-data")
    return str(db_path)


async def _record_backup(
    migrated_client, database_path: str, *, backup_id: str | None = None
) -> str:
    """Record a backup snapshot through the REST API and return the backup_id."""

    payload: dict[str, object] = {
        "database_path": database_path,
        "notes": "seed",
    }
    if backup_id:
        payload["backup_id"] = backup_id
    r = await migrated_client.post(
        "/admin/backup-snapshots:record",
        json=payload,
        headers=_owner_headers(),
    )
    assert r.status_code in (200, 201), r.text
    body = r.json()
    return body["backup_id"]


@pytest.mark.asyncio
async def test_get_backup_snapshot_not_found(migrated_client):
    r = await migrated_client.get(
        "/admin/backup-snapshots/missing-backup",
        headers=_owner_headers(),
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_backup_snapshot_forbidden_for_analyst(migrated_client):
    r = await migrated_client.get(
        "/admin/backup-snapshots/anything",
        headers=_analyst_headers(),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_get_backup_snapshot_forbidden_for_viewer(migrated_client):
    r = await migrated_client.get(
        "/admin/backup-snapshots/anything",
        headers=_viewer_headers(),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_get_backup_snapshot_returns_saved_record(migrated_client, tmp_path):
    path = _seed_backup_file(tmp_path)
    backup_id = await _record_backup(migrated_client, path)
    r = await migrated_client.get(
        f"/admin/backup-snapshots/{backup_id}",
        headers=_owner_headers(),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["snapshot"]["backup_id"] == backup_id
    assert body["snapshot"]["verification_status"] == "recorded"


@pytest.mark.asyncio
async def test_dry_run_restore_succeeds(migrated_client, tmp_path):
    path = _seed_backup_file(tmp_path)
    backup_id = await _record_backup(migrated_client, path)
    r = await migrated_client.post(
        f"/admin/backup-snapshots/{backup_id}:restore:dry-run",
        headers=_owner_headers(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["backup_id"] == backup_id
    assert body["status"] == "succeeded"
    assert body["manifest_hash"] != ""


@pytest.mark.asyncio
async def test_dry_run_restore_rejects_missing_backup(migrated_client):
    r = await migrated_client.post(
        "/admin/backup-snapshots/missing-backup:restore:dry-run",
        headers=_owner_headers(),
    )
    assert r.status_code == 400
    assert "BACKUP_NOT_FOUND" in r.json()["detail"]


@pytest.mark.asyncio
async def test_dry_run_restore_forbidden_for_analyst(migrated_client, tmp_path):
    path = _seed_backup_file(tmp_path)
    backup_id = await _record_backup(migrated_client, path)
    r = await migrated_client.post(
        f"/admin/backup-snapshots/{backup_id}:restore:dry-run",
        headers=_analyst_headers(),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_restore_backup_requires_accepted_by(migrated_client, tmp_path):
    path = _seed_backup_file(tmp_path)
    backup_id = await _record_backup(migrated_client, path)
    r = await migrated_client.post(
        f"/admin/backup-snapshots/{backup_id}:restore",
        json={"accepted_by": "owner-1"},
        headers=_owner_headers(),
    )
    # The bounded restore path refuses to overwrite
    # while the environment mode is not `paused`.
    assert r.status_code == 409
    assert "RESTORE_MODE_NOT_PAUSED" in r.json()["detail"]


@pytest.mark.asyncio
async def test_restore_backup_rejects_missing_accepted_by(migrated_client):
    # Pydantic validation rejects empty `accepted_by` with 422.
    r = await migrated_client.post(
        "/admin/backup-snapshots/any:restore",
        json={"accepted_by": ""},
        headers=_owner_headers(),
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_schedule_rehearsal_succeeds(migrated_client, tmp_path):
    path = _seed_backup_file(tmp_path)
    backup_id = await _record_backup(migrated_client, path)
    r = await migrated_client.post(
        f"/admin/backup-snapshots/{backup_id}:rehearsal",
        headers=_owner_headers(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["backup_id"] == backup_id
    assert body["mode"] == "rehearsal"
    assert body["status"] == "pending"


@pytest.mark.asyncio
async def test_schedule_rehearsal_rejects_missing_backup(migrated_client):
    r = await migrated_client.post(
        "/admin/backup-snapshots/missing:rehearsal",
        headers=_owner_headers(),
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_list_backup_restore_runs_returns_empty(migrated_client):
    r = await migrated_client.get(
        "/admin/backup-restore-runs",
        headers=_owner_headers(),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert body["total"] == 0


@pytest.mark.asyncio
async def test_list_backup_restore_runs_forbidden_for_analyst(migrated_client):
    r = await migrated_client.get(
        "/admin/backup-restore-runs",
        headers=_analyst_headers(),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_get_retention_policy_default(migrated_client):
    r = await migrated_client.get(
        "/admin/retention/policy",
        headers=_owner_headers(),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["backup_retention_days"] == 30
    assert body["audit_retention_days"] == 90
    assert body["prune_enabled"] is False


@pytest.mark.asyncio
async def test_put_retention_policy_rejects_audit_floor_violation(migrated_client):
    r = await migrated_client.put(
        "/admin/retention/policy",
        json={"audit_retention_days": 30},
        headers=_owner_headers(),
    )
    assert r.status_code == 400
    assert "audit_retention_days_below_floor" in r.json()["detail"]


@pytest.mark.asyncio
async def test_put_retention_policy_rejects_prune_without_acceptance(
    migrated_client,
):
    r = await migrated_client.put(
        "/admin/retention/policy",
        json={"prune_enabled": True},
        headers=_owner_headers(),
    )
    assert r.status_code == 409
    assert "RETENTION_ACCEPTANCE_REQUIRED" in r.json()["detail"]


@pytest.mark.asyncio
async def test_put_retention_policy_enables_prune_with_acceptance(migrated_client):
    r = await migrated_client.put(
        "/admin/retention/policy",
        json={"prune_enabled": True, "accepted_by": "owner-1"},
        headers=_owner_headers(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["prune_enabled"] is True
    assert body["accepted_by"] == "owner-1"


@pytest.mark.asyncio
async def test_retention_prune_rejected_when_disabled(migrated_client):
    r = await migrated_client.post(
        "/admin/retention/prune",
        json={"accepted_by": "owner-1"},
        headers=_owner_headers(),
    )
    assert r.status_code == 409
    assert "RETENTION_ACCEPTANCE_REQUIRED" in r.json()["detail"]


@pytest.mark.asyncio
async def test_data_deletion_requires_acceptance(migrated_client):
    r = await migrated_client.post(
        "/admin/data-deletion",
        json={
            "target": "lead",
            "target_id": "any",
            "accepted_by": "owner-1",
            "reason": "GDPR right-to-erasure",
        },
        headers=_owner_headers(),
    )
    # The lead does not exist; the path returns 400.
    assert r.status_code == 400
    assert "LEAD_NOT_FOUND" in r.json()["detail"]


@pytest.mark.asyncio
async def test_data_deletion_rejects_missing_reason(migrated_client):
    # Pydantic validation rejects empty `reason` with 422.
    r = await migrated_client.post(
        "/admin/data-deletion",
        json={
            "target": "lead",
            "target_id": "any",
            "accepted_by": "owner-1",
            "reason": "",
        },
        headers=_owner_headers(),
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_data_deletion_rejects_unknown_target(migrated_client):
    r = await migrated_client.post(
        "/admin/data-deletion",
        json={
            "target": "not_a_target",
            "target_id": "any",
            "accepted_by": "owner-1",
            "reason": "GDPR right-to-erasure",
        },
        headers=_owner_headers(),
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_data_deletion_forbidden_for_analyst(migrated_client):
    r = await migrated_client.post(
        "/admin/data-deletion",
        json={
            "target": "lead",
            "target_id": "any",
            "accepted_by": "owner-1",
            "reason": "GDPR right-to-erasure",
        },
        headers=_analyst_headers(),
    )
    assert r.status_code == 403
