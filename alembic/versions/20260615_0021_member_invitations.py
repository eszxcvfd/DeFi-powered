"""member invitations table (US-028)

Revision ID: 20260615_0021
Revises: 20260615_0020
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260615_0021"
down_revision: str | Sequence[str] | None = "20260615_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "member_invitations" not in tables:
        op.create_table(
            "member_invitations",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), nullable=False),
            sa.Column("email", sa.String(320), nullable=False),
            sa.Column("role", sa.String(32), nullable=False),
            sa.Column("state", sa.String(32), nullable=False, server_default="pending"),
            sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
            sa.Column("invited_by_user_id", sa.String(36), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("accepted_by_user_id", sa.String(36), nullable=True),
            sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_by_user_id", sa.String(36), nullable=True),
            sa.Column("revoke_reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index(
            "ix_member_invitations_token_hash",
            "member_invitations",
            ["token_hash"],
            unique=True,
        )
        op.create_index(
            "ix_member_invitations_organization_id",
            "member_invitations",
            ["organization_id"],
        )
        op.create_index(
            "ix_member_invitations_email",
            "member_invitations",
            ["email"],
        )
        op.create_index(
            "ix_member_invitations_state",
            "member_invitations",
            ["state"],
        )
        op.create_index(
            "ix_member_invitations_expires_at",
            "member_invitations",
            ["expires_at"],
        )
        op.create_index(
            "ix_member_invitations_invited_by_user_id",
            "member_invitations",
            ["invited_by_user_id"],
        )


def downgrade() -> None:
    op.drop_table("member_invitations")
