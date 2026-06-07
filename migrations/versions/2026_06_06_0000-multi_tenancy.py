"""multi_tenancy.

Revision ID: a1b2c3d4e5f6
Revises: 415a8f855e14
Create Date: 2026-06-06 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "415a8f855e14"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """FORK: multi-tenancy — Add auth tables and user_id FKs."""
    # Auth tables
    op.create_table(
        "auth_user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=256), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("avatar_url", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auth_user_email", "auth_user", ["email"], unique=True)
    op.create_index("ix_auth_user_id", "auth_user", ["id"], unique=False)

    op.create_table(
        "auth_oauth_account",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_user_id", sa.String(length=256), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["auth_user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_user_id"),
    )
    op.create_index("ix_auth_oauth_account_id", "auth_oauth_account", ["id"], unique=False)
    op.create_index("ix_auth_oauth_account_user_id", "auth_oauth_account", ["user_id"], unique=False)

    op.create_table(
        "auth_api_token",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["auth_user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_auth_api_token_id", "auth_api_token", ["id"], unique=False)
    op.create_index("ix_auth_api_token_token_hash", "auth_api_token", ["token_hash"], unique=True)
    op.create_index("ix_auth_api_token_user_id", "auth_api_token", ["user_id"], unique=False)

    op.create_table(
        "auth_share_link",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=256), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["auth_user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index("ix_auth_share_link_id", "auth_share_link", ["id"], unique=False)
    op.create_index("ix_auth_share_link_token", "auth_share_link", ["token"], unique=True)
    op.create_index("ix_auth_share_link_user_id", "auth_share_link", ["user_id"], unique=False)

    op.create_table(
        "user_setting",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("last_updated", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["auth_user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "key"),
    )
    op.create_index("ix_user_setting_id", "user_setting", ["id"], unique=False)
    op.create_index("ix_user_setting_user_id", "user_setting", ["user_id"], unique=False)

    # Add user_id to existing tables (nullable for backward compatibility)
    # FK constraints are skipped for SQLite (not supported via ALTER TABLE)
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    op.add_column("vendor", sa.Column("user_id", sa.Integer(), nullable=True))
    if not is_sqlite:
        op.create_foreign_key("fk_vendor_user_id", "vendor", "auth_user", ["user_id"], ["id"])
    op.create_index("ix_vendor_user_id", "vendor", ["user_id"], unique=False)

    op.add_column("filament", sa.Column("user_id", sa.Integer(), nullable=True))
    if not is_sqlite:
        op.create_foreign_key("fk_filament_user_id", "filament", "auth_user", ["user_id"], ["id"])
    op.create_index("ix_filament_user_id", "filament", ["user_id"], unique=False)

    op.add_column("spool", sa.Column("user_id", sa.Integer(), nullable=True))
    if not is_sqlite:
        op.create_foreign_key("fk_spool_user_id", "spool", "auth_user", ["user_id"], ["id"])
    op.create_index("ix_spool_user_id", "spool", ["user_id"], unique=False)


def downgrade() -> None:
    """Remove multi-tenancy tables and columns."""
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    op.drop_index("ix_spool_user_id", table_name="spool")
    if not is_sqlite:
        op.drop_constraint("fk_spool_user_id", "spool", type_="foreignkey")
    op.drop_column("spool", "user_id")

    op.drop_index("ix_filament_user_id", table_name="filament")
    if not is_sqlite:
        op.drop_constraint("fk_filament_user_id", "filament", type_="foreignkey")
    op.drop_column("filament", "user_id")

    op.drop_index("ix_vendor_user_id", table_name="vendor")
    if not is_sqlite:
        op.drop_constraint("fk_vendor_user_id", "vendor", type_="foreignkey")
    op.drop_column("vendor", "user_id")

    op.drop_index("ix_user_setting_user_id", table_name="user_setting")
    op.drop_index("ix_user_setting_id", table_name="user_setting")
    op.drop_table("user_setting")

    op.drop_index("ix_auth_share_link_user_id", table_name="auth_share_link")
    op.drop_index("ix_auth_share_link_token", table_name="auth_share_link")
    op.drop_index("ix_auth_share_link_id", table_name="auth_share_link")
    op.drop_table("auth_share_link")

    op.drop_index("ix_auth_api_token_user_id", table_name="auth_api_token")
    op.drop_index("ix_auth_api_token_token_hash", table_name="auth_api_token")
    op.drop_index("ix_auth_api_token_id", table_name="auth_api_token")
    op.drop_table("auth_api_token")

    op.drop_index("ix_auth_oauth_account_user_id", table_name="auth_oauth_account")
    op.drop_index("ix_auth_oauth_account_id", table_name="auth_oauth_account")
    op.drop_table("auth_oauth_account")

    op.drop_index("ix_auth_user_email", table_name="auth_user")
    op.drop_index("ix_auth_user_id", table_name="auth_user")
    op.drop_table("auth_user")
