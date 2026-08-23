"""Add local charging preferences for ChargeAmps bridge chargers."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "009_ev_charger_local_prefs"
down_revision: str | None = "008_ev_charger_override"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ev_chargers",
        sa.Column("charging_mode", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "ev_chargers",
        sa.Column("departure_time", sa.String(length=8), nullable=True),
    )
    op.add_column(
        "ev_chargers",
        sa.Column("target_soc_pct", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ev_chargers", "target_soc_pct")
    op.drop_column("ev_chargers", "departure_time")
    op.drop_column("ev_chargers", "charging_mode")
