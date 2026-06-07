"""admin role and shared vendor/filament catalog.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-07 00:01:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_admin to auth_user (guard against duplicate if column was added manually)
    conn = op.get_bind()
    cols = [row[1] for row in conn.execute(sa.text("PRAGMA table_info(auth_user)"))]
    if "is_admin" not in cols:
        op.add_column("auth_user", sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="0"))

    # Make vendor/filament global — drop user_id FK columns
    vendor_cols = [row[1] for row in conn.execute(sa.text("PRAGMA table_info(vendor)"))]
    if "user_id" in vendor_cols:
        vendor_indexes = [row[1] for row in conn.execute(sa.text("PRAGMA index_list(vendor)"))]
        with op.batch_alter_table("vendor") as batch_op:
            if "ix_vendor_user_id" in vendor_indexes:
                batch_op.drop_index("ix_vendor_user_id")
            batch_op.drop_column("user_id")

    filament_cols = [row[1] for row in conn.execute(sa.text("PRAGMA table_info(filament)"))]
    if "user_id" in filament_cols:
        filament_indexes = [row[1] for row in conn.execute(sa.text("PRAGMA index_list(filament)"))]
        with op.batch_alter_table("filament") as batch_op:
            if "ix_filament_user_id" in filament_indexes:
                batch_op.drop_index("ix_filament_user_id")
            batch_op.drop_column("user_id")


def downgrade() -> None:
    with op.batch_alter_table("filament") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_filament_user_id", ["user_id"])

    with op.batch_alter_table("vendor") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_vendor_user_id", ["user_id"])

    op.drop_column("auth_user", "is_admin")
