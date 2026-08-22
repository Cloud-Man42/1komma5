"""Add EV bridge settings to ev_chargers."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_ev_bridge_settings"
down_revision: Union[str, None] = "004_ev_chargers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ev_chargers", sa.Column("bridge_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("ev_chargers", sa.Column("bridge_mode", sa.String(length=32), nullable=False, server_default="auto"))
    op.add_column("ev_chargers", sa.Column("max_current_a", sa.Float(), nullable=False, server_default="16"))
    op.add_column("ev_chargers", sa.Column("min_current_a", sa.Float(), nullable=False, server_default="6"))
    op.add_column("ev_chargers", sa.Column("phases", sa.Integer(), nullable=False, server_default="3"))
    op.add_column("ev_chargers", sa.Column("nominal_voltage_v", sa.Float(), nullable=False, server_default="230"))
    op.add_column("ev_chargers", sa.Column("max_power_w", sa.Float(), nullable=True))
    op.add_column("ev_chargers", sa.Column("max_grid_import_w", sa.Float(), nullable=True))
    op.add_column("ev_chargers", sa.Column("update_interval_seconds", sa.Integer(), nullable=False, server_default="30"))
    op.add_column("ev_chargers", sa.Column("min_change_interval_seconds", sa.Integer(), nullable=False, server_default="60"))
    op.add_column("ev_chargers", sa.Column("current_hysteresis_a", sa.Float(), nullable=False, server_default="1"))
    op.add_column("ev_chargers", sa.Column("stale_timeout_seconds", sa.Integer(), nullable=False, server_default="120"))
    op.add_column("ev_chargers", sa.Column("chargeamps_api_key", sa.String(length=512), nullable=False, server_default=""))
    op.add_column("ev_chargers", sa.Column("last_applied_current_a", sa.Float(), nullable=True))
    op.add_column("ev_chargers", sa.Column("last_bridge_run_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ev_chargers", sa.Column("last_heartbeat_data_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("ev_chargers", "last_heartbeat_data_at")
    op.drop_column("ev_chargers", "last_bridge_run_at")
    op.drop_column("ev_chargers", "last_applied_current_a")
    op.drop_column("ev_chargers", "chargeamps_api_key")
    op.drop_column("ev_chargers", "stale_timeout_seconds")
    op.drop_column("ev_chargers", "current_hysteresis_a")
    op.drop_column("ev_chargers", "min_change_interval_seconds")
    op.drop_column("ev_chargers", "update_interval_seconds")
    op.drop_column("ev_chargers", "max_grid_import_w")
    op.drop_column("ev_chargers", "max_power_w")
    op.drop_column("ev_chargers", "nominal_voltage_v")
    op.drop_column("ev_chargers", "phases")
    op.drop_column("ev_chargers", "min_current_a")
    op.drop_column("ev_chargers", "max_current_a")
    op.drop_column("ev_chargers", "bridge_mode")
    op.drop_column("ev_chargers", "bridge_enabled")
