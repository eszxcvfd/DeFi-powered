"""browser_session_actions (US-021)

Revision ID: 20260614_0014
Revises: 20260614_0013
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260614_0014"
down_revision: str | Sequence[str] | None = "20260614_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "browser_session_actions" in insp.get_table_names():
        return
    op.create_table(
        "browser_session_actions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), nullable=False, index=True),
        sa.Column("organization_id", sa.String(36), nullable=False, index=True),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("action_type", sa.String(32), nullable=False),
        sa.Column("parameters_json", sa.Text(), server_default="{}"),
        sa.Column("lifecycle", sa.String(32), nullable=False),
        sa.Column("summary", sa.Text(), server_default=""),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("policy_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("browser_session_actions")
