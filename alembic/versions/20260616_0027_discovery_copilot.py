"""discovery copilot responses (US-037)

Revision ID: 20260616_0027
Revises: 20260616_0026
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260616_0027"
down_revision: str | Sequence[str] | None = "20260616_0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    if "discovery_copilot_responses" not in tables:
        op.create_table(
            "discovery_copilot_responses",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), nullable=False),
            sa.Column("campaign_id", sa.String(36), nullable=False),
            sa.Column("question", sa.Text(), nullable=False),
            sa.Column("response_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("provider_id", sa.String(64), nullable=False),
            sa.Column("model_id", sa.String(64), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
            sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("accepted_by", sa.String(128), nullable=True),
            sa.Column("query_expansion_set_id", sa.String(36), nullable=True),
            sa.Column("created_by", sa.String(128), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index(
            "ix_discovery_copilot_responses_organization_id",
            "discovery_copilot_responses",
            ["organization_id"],
        )
        op.create_index(
            "ix_discovery_copilot_responses_campaign_id",
            "discovery_copilot_responses",
            ["campaign_id"],
        )
        op.create_index(
            "ix_discovery_copilot_responses_query_expansion_set_id",
            "discovery_copilot_responses",
            ["query_expansion_set_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    if "discovery_copilot_responses" in tables:
        op.drop_table("discovery_copilot_responses")