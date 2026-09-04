"""Store operator price on vehicle charge sessions."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "054_vehicle_session_pricing"
down_revision = "053_vehicle_integration_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("vehicle_charge_sessions") as batch:
        batch.add_column(sa.Column("price_model", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("price_value_sek_kwh", sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("vehicle_charge_sessions") as batch:
        batch.drop_column("price_value_sek_kwh")
        batch.drop_column("price_model")
