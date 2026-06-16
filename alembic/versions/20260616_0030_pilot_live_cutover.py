"""pilot live cutover (US-040) — backup snapshots, live integration toggles,
cutover events, and worker heartbeats.

Revision ID: 20260616_0030
Revises: 20260616_0029
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260616_0030"
down_revision: str | Sequence[str] | None = "20260616_0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "backup_snapshots" not in tables:
        op.create_table(
            "backup_snapshots",
            sa.Column("backup_id", sa.String(96), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("database_path", sa.String(1024), nullable=False),
            sa.Column("database_size_bytes", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("verification_status", sa.String(32), nullable=False, server_default="recorded"),
            sa.Column("notes", sa.Text(), server_default=""),
            sa.Column("recorded_by", sa.String(128), server_default=""),
            sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("verified_by", sa.String(128), nullable=True),
            sa.Column("source", sa.String(64), server_default="operator"),
        )
        op.create_index(
            "ix_backup_snapshots_created_at",
            "backup_snapshots",
            ["created_at"],
        )
        op.create_index(
            "ix_backup_snapshots_verification_status",
            "backup_snapshots",
            ["verification_status"],
        )
        op.create_index(
            "ix_backup_snapshots_source",
            "backup_snapshots",
            ["source"],
        )

    if "live_integration_toggles" not in tables:
        op.create_table(
            "live_integration_toggles",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), nullable=False),
            sa.Column("integration", sa.String(64), nullable=False),
            sa.Column("state", sa.String(16), nullable=False, server_default="disabled"),
            sa.Column("previous_state", sa.String(16), server_default="disabled"),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_by", sa.String(128), server_default=""),
            sa.Column("approval_note", sa.Text(), server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint(
                "organization_id",
                "integration",
                name="uq_live_integration_toggles_org_integration",
            ),
        )
        op.create_index(
            "ix_live_integration_toggles_organization_id",
            "live_integration_toggles",
            ["organization_id"],
        )
        op.create_index(
            "ix_live_integration_toggles_integration",
            "live_integration_toggles",
            ["integration"],
        )

    if "cutover_events" not in tables:
        op.create_table(
            "cutover_events",
            sa.Column("event_id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), nullable=False),
            sa.Column("action", sa.String(32), nullable=False),
            sa.Column("previous_mode", sa.String(32), nullable=False),
            sa.Column("new_mode", sa.String(32), nullable=False),
            sa.Column("actor", sa.String(128), nullable=False),
            sa.Column("actor_role", sa.String(64), server_default=""),
            sa.Column("reason", sa.Text(), nullable=False, server_default=""),
            sa.Column("notes", sa.Text(), server_default=""),
            sa.Column("gate_passed", sa.Boolean(), server_default=sa.text("0")),
            sa.Column("gate_summary", sa.Text(), server_default=""),
            sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index(
            "ix_cutover_events_organization_id",
            "cutover_events",
            ["organization_id"],
        )
        op.create_index(
            "ix_cutover_events_action",
            "cutover_events",
            ["action"],
        )
        op.create_index(
            "ix_cutover_events_occurred_at",
            "cutover_events",
            ["occurred_at"],
        )

    if "worker_heartbeats" not in tables:
        op.create_table(
            "worker_heartbeats",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("worker_id", sa.String(64), nullable=False),
            sa.Column("last_seen", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("last_task", sa.String(96), server_default=""),
            sa.Column("detail", sa.Text(), server_default=""),
            sa.Column("organization_id", sa.String(36), server_default=""),
        )
        op.create_index(
            "ix_worker_heartbeats_worker_id",
            "worker_heartbeats",
            ["worker_id"],
        )
        op.create_index(
            "ix_worker_heartbeats_last_seen",
            "worker_heartbeats",
            ["last_seen"],
        )
        op.create_index(
            "ix_worker_heartbeats_organization_id",
            "worker_heartbeats",
            ["organization_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    if "worker_heartbeats" in tables:
        op.drop_table("worker_heartbeats")
    if "cutover_events" in tables:
        op.drop_table("cutover_events")
    if "live_integration_toggles" in tables:
        op.drop_table("live_integration_toggles")
    if "backup_snapshots" in tables:
        op.drop_table("backup_snapshots")
