"""Local filesystem store for browser debug artifact blobs (US-023)."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID


def artifact_root(base: Path) -> Path:
    root = base / "browser_artifacts"
    root.mkdir(parents=True, exist_ok=True)
    return root


def session_artifact_dir(base: Path, organization_id: UUID, session_id: UUID) -> Path:
    d = artifact_root(base) / str(organization_id) / str(session_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_blob(base: Path, organization_id: UUID, session_id: UUID, artifact_id: UUID, data: bytes, ext: str) -> Path:
    d = session_artifact_dir(base, organization_id, session_id)
    path = d / f"{artifact_id}.{ext}"
    path.write_bytes(data)
    return path


def read_blob(storage_path: Path) -> bytes:
    return storage_path.read_bytes()


def relative_storage_key(path: Path, base: Path) -> str:
    try:
        return str(path.resolve().relative_to(artifact_root(base).resolve()))
    except ValueError:
        return str(path.name)