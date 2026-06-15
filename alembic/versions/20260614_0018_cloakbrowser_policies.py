"""cloakbrowser source-scoped policy (US-025)

Revision ID: 20260614_0018
Revises: 20260614_0017
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260614_0018"
down_revision: str | Sequence[str] | None = "20260614_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "cloakbrowser_policies" not in insp.get_table_names():
        op.create_table(
            "cloakbrowser_policies",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), nullable=False, index=True),
            sa.Column("source_id", sa.String(36), nullable=False, index=True),
            sa.Column("purpose_rationale", sa.Text(), nullable=False, server_default=""),
            sa.Column("owner_admin_approved", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("compliance_approved", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("owner_admin_actor", sa.String(128), nullable=True),
            sa.Column("compliance_actor", sa.String(128), nullable=True),
            sa.Column("owner_admin_approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("compliance_approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_by", sa.String(128), nullable=True),
            sa.Column("revoke_reason", sa.Text(), nullable=True),
            sa.Column("pinned_version", sa.String(64), nullable=True),
            sa.Column("expected_checksum", sa.String(128), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table("cloakbrowser_policies")