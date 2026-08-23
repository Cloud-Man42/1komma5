"""Drop the EV energy need column — the car stops itself at its target SoC."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "026_drop_required_energy_kwh"
down_revision: str | None = "025_balanced_solar_thresholds"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("ev_chargers") as batch:
        batch.drop_column("required_energy_kwh")


def downgrade() -> None:
    with op.batch_alter_table("ev_chargers") as batch:
        batch.add_column(sa.Column("required_energy_kwh", sa.Float(), nullable=True))
