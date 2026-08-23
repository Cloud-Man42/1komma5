"""Add energy_devices table for Modbus inverter configuration."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "011_energy_devices"
down_revision: str | None = "010_ev_bridge_cycles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "energy_devices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("protocol", sa.String(length=16), nullable=False, server_default="modbus-tcp"),
        sa.Column("host", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("port", sa.Integer(), nullable=False, server_default="502"),
        sa.Column("unit_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("manufacturer", sa.String(length=64), nullable=False, server_default="Sungrow"),
        sa.Column("model", sa.String(length=64), nullable=False, server_default="SH10RT"),
        sa.Column(
            "register_profile", sa.String(length=32), nullable=False, server_default="hybrid_sh10rt"
        ),
        sa.Column("poll_interval_ms", sa.Integer(), nullable=False, server_default="3000"),
        sa.Column("stale_timeout_s", sa.Integer(), nullable=False, server_default="120"),
        sa.Column("merge_mode", sa.String(length=32), nullable=False, server_default="complement"),
        sa.Column("mock_mode", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("detected_device_code", sa.Integer(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("extended_snapshot", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_energy_devices_site_id", "energy_devices", ["site_id"])


def downgrade() -> None:
    op.drop_index("ix_energy_devices_site_id", table_name="energy_devices")
    op.drop_table("energy_devices")
