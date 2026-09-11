"""063 — installed module packages registry."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "063_installed_module_packages"
down_revision = "062_site_module_configurations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "installed_module_packages",
        sa.Column("module_id", sa.String(length=128), primary_key=True),
        sa.Column("installed_version", sa.String(length=64), nullable=False),
        sa.Column("package_state", sa.String(length=32), nullable=False, server_default="installed"),
        sa.Column("package_path", sa.Text(), nullable=False),
        sa.Column("staging_path", sa.Text(), nullable=True),
        sa.Column("publisher", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="upload"),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("signature_status", sa.String(length=16), nullable=False, server_default="unsigned"),
        sa.Column("rollback_version", sa.String(length=64), nullable=True),
        sa.Column("previous_package_path", sa.Text(), nullable=True),
        sa.Column("module_api_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("restart_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("installed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("installed_module_packages")
