"""Initial schema: sites and energy_readings."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sites",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("external_system_id", sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_sites_slug", "sites", ["slug"], unique=True)

    op.create_table(
        "energy_readings",
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("solar_production_w", sa.Float(), nullable=False),
        sa.Column("consumption_w", sa.Float(), nullable=False),
        sa.Column("grid_import_w", sa.Float(), nullable=False),
        sa.Column("grid_export_w", sa.Float(), nullable=False),
        sa.Column("battery_soc_pct", sa.Float(), nullable=False),
        sa.Column("battery_power_w", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("site_id", "recorded_at"),
    )
    op.create_index("ix_energy_readings_recorded_at", "energy_readings", ["recorded_at"])


def downgrade() -> None:
    op.drop_index("ix_energy_readings_recorded_at", table_name="energy_readings")
    op.drop_table("energy_readings")
    op.drop_index("ix_sites_slug", table_name="sites")
    op.drop_table("sites")
