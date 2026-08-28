"""Correct the supplied 2025 history source to Tibber."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "015_tibber_history_source"
down_revision: str | None = "014_historical_monthly_energy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    historical_energy = sa.table(
        "historical_monthly_energy",
        sa.column("source", sa.String()),
    )
    op.execute(
        historical_energy.update()
        .where(
            historical_energy.c.source.in_(
                ["E.ON Historik 2025", "E.ON Historik 2025 (bild)"]
            )
        )
        .values(source="Demo import baseline 2025")
    )


def downgrade() -> None:
    historical_energy = sa.table(
        "historical_monthly_energy",
        sa.column("source", sa.String()),
    )
    op.execute(
        historical_energy.update()
        .where(historical_energy.c.source == "Demo import baseline 2025")
        .values(source="E.ON Historik 2025 (bild)")
    )
