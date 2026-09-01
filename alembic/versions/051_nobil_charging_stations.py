"""Migration 051: charging stations, lookup cache, session extensions.

Legacy migration – NOBIL integration removed in 052; generic tables retained.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "051_nobil_charging_stations"
down_revision = "050_charging_session_intelligence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "charging_station",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("provider", sa.String(length=16), nullable=False, server_default="NOBIL"),
        sa.Column("provider_station_id", sa.String(length=64), nullable=False),
        sa.Column("operator", sa.String(length=128), nullable=True),
        sa.Column("station_name", sa.String(length=256), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("address", sa.String(length=256), nullable=True),
        sa.Column("postal_code", sa.String(length=16), nullable=True),
        sa.Column("city", sa.String(length=128), nullable=True),
        sa.Column("country", sa.String(length=8), nullable=True),
        sa.Column("connector_type", sa.String(length=64), nullable=True),
        sa.Column("max_power_kw", sa.Float(), nullable=True),
        sa.Column("charging_type", sa.String(length=16), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("times_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("user_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("raw_provider_data", sa.JSON(), nullable=True),
        sa.UniqueConstraint("provider", "provider_station_id", name="uq_charging_station_provider_id"),
    )
    op.create_index("ix_charging_station_provider_id", "charging_station", ["provider_station_id"])

    op.create_table(
        "charging_station_lookup_cache",
        sa.Column("geohash_key", sa.String(length=12), primary_key=True),
        sa.Column("latitude_rounded", sa.Float(), nullable=False),
        sa.Column("longitude_rounded", sa.Float(), nullable=False),
        sa.Column("radius_m", sa.Integer(), nullable=False),
        sa.Column("resolved_json", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "nobil_integration_status",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_latency_ms", sa.Integer(), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(length=512), nullable=True),
        sa.Column("cache_hits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cache_misses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("requests_last_hour", sa.Integer(), nullable=False, server_default="0"),
    )

    with op.batch_alter_table("vehicle_charge_sessions") as batch:
        batch.add_column(sa.Column("charging_station_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("station_provider", sa.String(length=16), nullable=True))
        batch.add_column(sa.Column("station_provider_id", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("station_name", sa.String(length=256), nullable=True))
        batch.add_column(sa.Column("distance_from_vehicle_m", sa.Float(), nullable=True))
        batch.add_column(sa.Column("station_confidence", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("station_resolution_status", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("station_candidates_json", sa.JSON(), nullable=True))

    op.execute(
        sa.text(
            """
            INSERT INTO charging_locations (
                site_id, name, classification, latitude, longitude, radius_m,
                expected_operator, expected_charging_type, price_model, enabled
            )
            SELECT 1, 'Hotel', 'HOTEL', 59.3293, 18.0686, 150,
                   'ChargeNode', 'AC', 'UNKNOWN', 1
            WHERE EXISTS (SELECT 1 FROM sites WHERE id = 1)
              AND NOT EXISTS (
                SELECT 1 FROM charging_locations WHERE site_id = 1 AND name = 'Hotel'
              )
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO charging_locations (
                site_id, name, classification, latitude, longitude, radius_m,
                expected_operator, expected_charging_type, price_model, enabled
            )
            SELECT 1, 'Summer House Denmark', 'HOME_SECONDARY', 55.6761, 12.5683, 150,
                   NULL, 'AC', 'UNKNOWN', 1
            WHERE EXISTS (SELECT 1 FROM sites WHERE id = 1)
              AND NOT EXISTS (
                SELECT 1 FROM charging_locations WHERE site_id = 1 AND name = 'Summer House Denmark'
              )
            """
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("vehicle_charge_sessions") as batch:
        for col in (
            "station_candidates_json",
            "station_resolution_status",
            "station_confidence",
            "distance_from_vehicle_m",
            "station_name",
            "station_provider_id",
            "station_provider",
            "charging_station_id",
        ):
            batch.drop_column(col)
    op.drop_table("nobil_integration_status")
    op.drop_table("charging_station_lookup_cache")
    op.drop_index("ix_charging_station_provider_id", table_name="charging_station")
    op.drop_table("charging_station")
