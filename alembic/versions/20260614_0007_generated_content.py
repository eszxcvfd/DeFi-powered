"""generated content drafts

Revision ID: 20260614_0007
Revises: 20260614_0006
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260614_0007"
down_revision: Union[str, Sequence[str], None] = "20260614_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if "generated_content_drafts" in sa.inspect(bind).get_table_names():
        return
    op.create_table(
        "generated_content_drafts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_id", sa.String(36), nullable=False, index=True),
        sa.Column("campaign_id", sa.String(36), nullable=False, index=True),
        sa.Column("engagement_plan_id", sa.String(36), nullable=True, index=True),
        sa.Column("variant_index", sa.Integer(), nullable=False),
        sa.Column("lifecycle", sa.String(32), server_default="draft"),
        sa.Column("settings_json", sa.Text(), server_default="{}"),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("risk_flags_json", sa.Text(), server_default="[]"),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("prompt_template_version", sa.String(64), nullable=False),
        sa.Column("input_context_summary", sa.Text(), server_default=""),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_editor", sa.String(128), server_default="system"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("generated_content_drafts")