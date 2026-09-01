"""Vehicle integration diagnostic event log."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "053_vehicle_integration_events"
down_revision = "052_chargefinder_integration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "vehicle_integration_events" in inspector.get_table_names():
        return
    op.create_table(
        "vehicle_integration_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vehicle_id", sa.Integer(), sa.ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False, server_default="INFO"),
        sa.Column("message", sa.String(512), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_vehicle_integration_events_site_id", "vehicle_integration_events", ["site_id"])
    op.create_index("ix_vehicle_integration_events_vehicle_id", "vehicle_integration_events", ["vehicle_id"])
    op.create_index("ix_vehicle_integration_events_recorded_at", "vehicle_integration_events", ["recorded_at"])


def downgrade() -> None:
    op.drop_index("ix_vehicle_integration_events_recorded_at", table_name="vehicle_integration_events")
    op.drop_index("ix_vehicle_integration_events_vehicle_id", table_name="vehicle_integration_events")
    op.drop_index("ix_vehicle_integration_events_site_id", table_name="vehicle_integration_events")
    op.drop_table("vehicle_integration_events")
