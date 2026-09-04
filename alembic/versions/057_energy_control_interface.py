"""Energy control interface foundation."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "057_energy_control_interface"
down_revision = "056_energy_forecast_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("sites") as batch:
        batch.add_column(
            sa.Column("energy_control_enabled", sa.Boolean(), nullable=False, server_default=sa.false())
        )

    op.create_table(
        "energy_control_actions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("optimization_mode", sa.String(length=32), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("target", sa.String(length=32), nullable=False, server_default="site"),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_energy_control_actions_site_recorded",
        "energy_control_actions",
        ["site_id", "recorded_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_energy_control_actions_site_recorded", table_name="energy_control_actions")
    op.drop_table("energy_control_actions")
    with op.batch_alter_table("sites") as batch:
        batch.drop_column("energy_control_enabled")
