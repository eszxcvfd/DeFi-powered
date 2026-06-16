"""ai feedback events (US-038)

Revision ID: 20260616_0028
Revises: 20260616_0027
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260616_0028"
down_revision: str | Sequence[str] | None = "20260616_0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    if "ai_feedback_events" not in tables:
        op.create_table(
            "ai_feedback_events",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), nullable=False),
            sa.Column("target_type", sa.String(64), nullable=False),
            sa.Column("target_id", sa.String(36), nullable=False),
            sa.Column("actor_key", sa.String(128), nullable=False),
            sa.Column("state", sa.String(32), nullable=False),
            sa.Column("reason_code", sa.String(64), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("prior_state", sa.String(32), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index(
            "ix_ai_feedback_events_organization_id",
            "ai_feedback_events",
            ["organization_id"],
        )
        op.create_index(
            "ix_ai_feedback_events_target",
            "ai_feedback_events",
            ["target_type", "target_id"],
        )
        op.create_index(
            "ix_ai_feedback_events_actor_target",
            "ai_feedback_events",
            ["organization_id", "actor_key", "target_type", "target_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    if "ai_feedback_events" in tables:
        op.drop_table("ai_feedback_events")