"""identity and access tables (US-027)

Revision ID: 20260615_0020
Revises: 20260614_0019
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260615_0020"
down_revision: str | Sequence[str] | None = "20260614_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("email", sa.String(320), nullable=False),
            sa.Column("email_hash", sa.String(64), nullable=False, unique=True),
            sa.Column("display_name", sa.String(200), nullable=False, server_default=""),
            sa.Column("password_hash", sa.String(256), nullable=False),
            sa.Column("password_salt", sa.String(64), nullable=False),
            sa.Column("password_iterations", sa.Integer(), nullable=False, server_default="200000"),
            sa.Column("disabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("failed_attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
        )
        op.create_index("ix_users_email_hash", "users", ["email_hash"], unique=True)
        op.create_index("ix_users_disabled", "users", ["disabled"])

    if "organization_memberships" not in tables:
        op.create_table(
            "organization_memberships",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), nullable=False),
            sa.Column("organization_id", sa.String(36), nullable=False),
            sa.Column("role", sa.String(32), nullable=False),
            sa.Column("state", sa.String(32), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
            sa.UniqueConstraint(
                "user_id", "organization_id", name="uq_org_membership_user_org"
            ),
        )
        op.create_index(
            "ix_organization_memberships_user_id", "organization_memberships", ["user_id"]
        )
        op.create_index(
            "ix_organization_memberships_organization_id",
            "organization_memberships",
            ["organization_id"],
        )
        op.create_index(
            "ix_organization_memberships_state", "organization_memberships", ["state"]
        )

    if "sessions" not in tables:
        op.create_table(
            "sessions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), nullable=False),
            sa.Column("organization_id", sa.String(36), nullable=False),
            sa.Column("role", sa.String(32), nullable=False),
            sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
            sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("client_ip", sa.String(64), nullable=False, server_default=""),
            sa.Column("user_agent", sa.String(300), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_sessions_token_hash", "sessions", ["token_hash"], unique=True)
        op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
        op.create_index("ix_sessions_organization_id", "sessions", ["organization_id"])
        op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"])
        op.create_index("ix_sessions_revoked_at", "sessions", ["revoked_at"])


def downgrade() -> None:
    op.drop_table("sessions")
    op.drop_table("organization_memberships")
    op.drop_table("users")
