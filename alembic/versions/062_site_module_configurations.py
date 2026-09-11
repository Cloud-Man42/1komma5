"""Site module configuration overlay."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "062_site_module_configurations"
down_revision = "061_admin_audit_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "site_module_configurations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("module_id", sa.String(length=64), nullable=False),
        sa.Column("enabled_override", sa.Boolean(), nullable=True),
        sa.Column("config_json", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("site_id", "module_id", name="uq_site_module"),
    )
    op.create_index("ix_site_module_configurations_site_id", "site_module_configurations", ["site_id"])


def downgrade() -> None:
    op.drop_index("ix_site_module_configurations_site_id", table_name="site_module_configurations")
    op.drop_table("site_module_configurations")
