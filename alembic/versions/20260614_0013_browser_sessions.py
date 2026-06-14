"""browser_sessions table (US-020)

Revision ID: 20260614_0013
Revises: 20260614_0012
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260614_0013"
down_revision: str | Sequence[str] | None = "20260614_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "browser_sessions" in insp.get_table_names():
        return
    op.create_table(
        "browser_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False, index=True),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("launch_kind", sa.String(16), nullable=False),
        sa.Column("event_id", sa.String(36), nullable=True, index=True),
        sa.Column("source_id", sa.String(36), nullable=False, index=True),
        sa.Column("initial_url", sa.String(1024), nullable=False),
        sa.Column("source_name", sa.String(200), server_default=""),
        sa.Column("source_domain", sa.String(255), server_default=""),
        sa.Column("engine", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, index=True),
        sa.Column("isolation_key", sa.String(128), nullable=False),
        sa.Column("profile_boundary", sa.String(256), nullable=False),
        sa.Column("current_url", sa.String(1024), server_default=""),
        sa.Column("latest_action_summary", sa.Text(), server_default=""),
        sa.Column("policy_reasons_json", sa.Text(), server_default="[]"),
        sa.Column("stop_requested", sa.Boolean(), server_default=sa.false()),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("worker_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("browser_sessions")
