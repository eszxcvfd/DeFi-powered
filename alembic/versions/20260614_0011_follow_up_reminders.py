"""follow-up reminders and history

Revision ID: 20260614_0011
Revises: 20260614_0010
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260614_0011"
down_revision: str | Sequence[str] | None = "20260614_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()
    if "follow_up_reminders" not in tables:
        op.create_table(
            "follow_up_reminders",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), nullable=False, index=True),
            sa.Column("lead_id", sa.String(36), nullable=False, index=True),
            sa.Column("owner", sa.String(128), server_default=""),
            sa.Column("due_date", sa.String(10), nullable=False, index=True),
            sa.Column("state", sa.String(32), server_default="scheduled", index=True),
            sa.Column("last_actor", sa.String(128), server_default=""),
            sa.Column("last_action_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
    if "reminder_history" not in tables:
        op.create_table(
            "reminder_history",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("reminder_id", sa.String(36), nullable=False, index=True),
            sa.Column("lead_id", sa.String(36), nullable=False, index=True),
            sa.Column("kind", sa.String(32), nullable=False),
            sa.Column("actor", sa.String(128), nullable=False),
            sa.Column("note", sa.Text(), server_default=""),
            sa.Column("from_due_date", sa.String(10), server_default=""),
            sa.Column("to_due_date", sa.String(10), server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table("reminder_history")
    op.drop_table("follow_up_reminders")
