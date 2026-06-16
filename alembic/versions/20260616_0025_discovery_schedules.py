"""discovery schedules and dispatch history (US-035)

Revision ID: 20260616_0025
Revises: 20260616_0024
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260616_0025"
down_revision: str | Sequence[str] | None = "20260616_0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "discovery_schedules" not in tables:
        op.create_table(
            "discovery_schedules",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), nullable=False),
            sa.Column("campaign_id", sa.String(36), nullable=False),
            sa.Column("enabled_state", sa.String(16), nullable=False, server_default="enabled"),
            sa.Column("recurrence_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("source_ids_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("template_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_dispatched_job_id", sa.String(36), nullable=True),
            sa.Column("last_dispatch_outcome", sa.String(64), nullable=True),
            sa.Column("overlap_policy", sa.String(32), nullable=False, server_default="skip_while_running"),
            sa.Column("created_by", sa.String(128), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_discovery_schedules_organization_id", "discovery_schedules", ["organization_id"])
        op.create_index("ix_discovery_schedules_campaign_id", "discovery_schedules", ["campaign_id"])
        op.create_index("ix_discovery_schedules_enabled_state", "discovery_schedules", ["enabled_state"])
        op.create_index("ix_discovery_schedules_next_run_at", "discovery_schedules", ["next_run_at"])

    if "discovery_schedule_dispatches" not in tables:
        op.create_table(
            "discovery_schedule_dispatches",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), nullable=False),
            sa.Column("schedule_id", sa.String(36), nullable=False),
            sa.Column("outcome", sa.String(32), nullable=False),
            sa.Column("discovery_job_id", sa.String(36), nullable=True),
            sa.Column("detail", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index(
            "ix_discovery_schedule_dispatches_schedule_id",
            "discovery_schedule_dispatches",
            ["schedule_id"],
        )

    cols = {c["name"] for c in insp.get_columns("discovery_jobs")} if "discovery_jobs" in tables else set()
    if "discovery_schedule_id" not in cols and "discovery_jobs" in tables:
        with op.batch_alter_table("discovery_jobs") as batch:
            batch.add_column(sa.Column("discovery_schedule_id", sa.String(36), nullable=True))
        op.create_index(
            "ix_discovery_jobs_discovery_schedule_id",
            "discovery_jobs",
            ["discovery_schedule_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    if "discovery_jobs" in tables:
        cols = {c["name"] for c in insp.get_columns("discovery_jobs")}
        if "discovery_schedule_id" in cols:
            op.drop_index("ix_discovery_jobs_discovery_schedule_id", table_name="discovery_jobs")
            with op.batch_alter_table("discovery_jobs") as batch:
                batch.drop_column("discovery_schedule_id")
    if "discovery_schedule_dispatches" in tables:
        op.drop_table("discovery_schedule_dispatches")
    if "discovery_schedules" in tables:
        op.drop_table("discovery_schedules")