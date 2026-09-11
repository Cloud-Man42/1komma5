"""064 — module publisher trust keys."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "064_module_publisher_keys"
down_revision = "063_installed_module_packages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "module_publisher_keys",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("publisher_id", sa.String(length=128), nullable=False),
        sa.Column("key_id", sa.String(length=64), nullable=False),
        sa.Column("public_key_hex", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="trusted"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_module_publisher_keys_publisher_id", "module_publisher_keys", ["publisher_id"])


def downgrade() -> None:
    op.drop_index("ix_module_publisher_keys_publisher_id", table_name="module_publisher_keys")
    op.drop_table("module_publisher_keys")
