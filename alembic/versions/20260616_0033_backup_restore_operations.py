"""Backup and restore operations baseline (US-043) — durable
`backup_restore_runs` and `retention_policies` tables
for the bounded restore, retention prune, and
data-deletion paths. The migration also adds the
`anonymized_at` / `anonymized_by` columns to
`leads`, the `disabled_at` / `disabled_by` columns
to `users`, and the `redacted_at` / `redacted_by`
columns to `event_source_observations` so the
`DataDeletionService` can mark records as
`anonymized`, `disabled`, or `redacted` without
cascading delete.

The migration is forward-only; the documented
rollback path is to drop the new tables and
columns. No existing rows are touched.

Revision ID: 20260616_0033
Revises: 20260616_0032
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260616_0033"
down_revision: str | Sequence[str] | None = "20260616_0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns(table_name)}
    return column_name in cols


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return table_name in set(insp.get_table_names())


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    # backup_restore_runs
    if "backup_restore_runs" not in tables:
        op.create_table(
            "backup_restore_runs",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("organization_id", sa.String(length=36), nullable=False),
            sa.Column("backup_id", sa.String(length=96), nullable=False),
            sa.Column(
                "started_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "status",
                sa.String(length=32),
                nullable=False,
                server_default="pending",
            ),
            sa.Column(
                "mode",
                sa.String(length=16),
                nullable=False,
                server_default="dry_run",
            ),
            sa.Column(
                "target_location",
                sa.Text(),
                nullable=False,
                server_default="",
            ),
            sa.Column(
                "manifest_hash",
                sa.String(length=128),
                nullable=False,
                server_default="",
            ),
            sa.Column(
                "row_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "audit_correlation_id",
                sa.String(length=64),
                nullable=False,
                server_default="",
            ),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        op.create_index(
            "ix_backup_restore_runs_org",
            "backup_restore_runs",
            ["organization_id"],
            unique=False,
        )
        op.create_index(
            "ix_backup_restore_runs_backup_id",
            "backup_restore_runs",
            ["backup_id"],
            unique=False,
        )
        op.create_index(
            "ix_backup_restore_runs_status",
            "backup_restore_runs",
            ["status"],
            unique=False,
        )

    # retention_policies
    if "retention_policies" not in tables:
        op.create_table(
            "retention_policies",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column(
                "organization_id", sa.String(length=36), nullable=False
            ),
            sa.Column(
                "backup_retention_days",
                sa.Integer(),
                nullable=False,
                server_default="30",
            ),
            sa.Column(
                "audit_retention_days",
                sa.Integer(),
                nullable=False,
                server_default="90",
            ),
            sa.Column(
                "prune_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column("accepted_by", sa.String(length=128), nullable=True),
            sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.UniqueConstraint(
                "organization_id",
                name="uq_retention_policies_org",
            ),
        )
        op.create_index(
            "ix_retention_policies_org",
            "retention_policies",
            ["organization_id"],
            unique=False,
        )

    # leads: anonymized_at, anonymized_by
    if "leads" in tables and not _has_column("leads", "anonymized_at"):
        op.add_column(
            "leads",
            sa.Column("anonymized_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "leads" in tables and not _has_column("leads", "anonymized_by"):
        op.add_column(
            "leads",
            sa.Column("anonymized_by", sa.String(length=128), nullable=True),
        )

    # users: disabled_at, disabled_by
    if "users" in tables and not _has_column("users", "disabled_at"):
        op.add_column(
            "users",
            sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "users" in tables and not _has_column("users", "disabled_by"):
        op.add_column(
            "users",
            sa.Column("disabled_by", sa.String(length=128), nullable=True),
        )

    # event_source_observations: redacted_at, redacted_by
    if "event_source_observations" in tables and not _has_column(
        "event_source_observations", "redacted_at"
    ):
        op.add_column(
            "event_source_observations",
            sa.Column("redacted_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "event_source_observations" in tables and not _has_column(
        "event_source_observations", "redacted_by"
    ):
        op.add_column(
            "event_source_observations",
            sa.Column("redacted_by", sa.String(length=128), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "event_source_observations" in tables and _has_column(
        "event_source_observations", "redacted_by"
    ):
        op.drop_column("event_source_observations", "redacted_by")
    if "event_source_observations" in tables and _has_column(
        "event_source_observations", "redacted_at"
    ):
        op.drop_column("event_source_observations", "redacted_at")
    if "users" in tables and _has_column("users", "disabled_by"):
        op.drop_column("users", "disabled_by")
    if "users" in tables and _has_column("users", "disabled_at"):
        op.drop_column("users", "disabled_at")
    if "leads" in tables and _has_column("leads", "anonymized_by"):
        op.drop_column("leads", "anonymized_by")
    if "leads" in tables and _has_column("leads", "anonymized_at"):
        op.drop_column("leads", "anonymized_at")
    if "retention_policies" in tables:
        op.drop_table("retention_policies")
    if "backup_restore_runs" in tables:
        op.drop_table("backup_restore_runs")
