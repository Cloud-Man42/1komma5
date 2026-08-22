"""Add manually supplied historical monthly energy."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "014_historical_monthly_energy"
down_revision: str | None = "013_financial_stats"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "historical_monthly_energy",
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("imported_kwh", sa.Float(), nullable=False),
        sa.Column("imported_cost_sek", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("estimated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.CheckConstraint("month >= 1 AND month <= 12", name="ck_historical_energy_month"),
        sa.CheckConstraint("imported_kwh >= 0", name="ck_historical_energy_imported_kwh"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("site_id", "year", "month"),
    )


def downgrade() -> None:
    op.drop_table("historical_monthly_energy")
