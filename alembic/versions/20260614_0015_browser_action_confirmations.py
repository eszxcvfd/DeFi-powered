"""browser_action_confirmations (US-022)

Revision ID: 20260614_0015
Revises: 20260614_0014
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260614_0015"
down_revision: str | Sequence[str] | None = "20260614_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "browser_action_confirmations" in insp.get_table_names():
        return
    op.create_table(
        "browser_action_confirmations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), nullable=False, index=True),
        sa.Column("organization_id", sa.String(36), nullable=False, index=True),
        sa.Column("requested_by", sa.String(128), nullable=False),
        sa.Column("action_type", sa.String(32), nullable=False),
        sa.Column("parameters_json", sa.Text(), server_default="{}"),
        sa.Column("preview_json", sa.Text(), server_default="{}"),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_by", sa.String(128), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", sa.String(128), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_action_id", sa.String(36), nullable=True),
        sa.Column("execution_lifecycle", sa.String(32), nullable=True),
        sa.Column("execution_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("browser_action_confirmations")