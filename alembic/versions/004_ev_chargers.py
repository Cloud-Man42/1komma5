"""Add EV charger configuration per site."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_ev_chargers"
down_revision: Union[str, None] = "003_heartbeat_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ev_chargers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("manufacturer", sa.String(length=64), nullable=False, server_default="ChargeAmps"),
        sa.Column("model", sa.String(length=64), nullable=False, server_default="Halo"),
        sa.Column("control_source", sa.String(length=16), nullable=False, server_default="heartbeat"),
        sa.Column("heartbeat_ev_id", sa.String(length=128), nullable=True),
        sa.Column("heartbeat_charger_id", sa.String(length=128), nullable=True),
        sa.Column("chargeamp_charger_id", sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_ev_chargers_site_id", "ev_chargers", ["site_id"])


def downgrade() -> None:
    op.drop_index("ix_ev_chargers_site_id", table_name="ev_chargers")
    op.drop_table("ev_chargers")
