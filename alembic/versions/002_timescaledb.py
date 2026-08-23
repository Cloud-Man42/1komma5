"""TimescaleDB hypertable and continuous aggregates (PostgreSQL only)."""

import os
from collections.abc import Sequence

from alembic import op

revision: str = "002_timescaledb"
down_revision: str | None = "001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    if os.environ.get("ENABLE_TIMESCALEDB", "false").lower() not in ("1", "true", "yes"):
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")
    op.execute(
        "SELECT create_hypertable('energy_readings', 'recorded_at', "
        "if_not_exists => TRUE, migrate_data => TRUE)"
    )
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS energy_readings_5min
        WITH (timescaledb.continuous) AS
        SELECT
            site_id,
            time_bucket('5 minutes', recorded_at) AS bucket,
            avg(solar_production_w) AS solar_production_w,
            avg(consumption_w) AS consumption_w,
            avg(grid_import_w) AS grid_import_w,
            avg(grid_export_w) AS grid_export_w,
            avg(battery_soc_pct) AS battery_soc_pct,
            avg(battery_power_w) AS battery_power_w
        FROM energy_readings
        GROUP BY site_id, bucket
        WITH NO DATA
    """)
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS energy_readings_1hour
        WITH (timescaledb.continuous) AS
        SELECT
            site_id,
            time_bucket('1 hour', recorded_at) AS bucket,
            avg(solar_production_w) AS solar_production_w,
            avg(consumption_w) AS consumption_w,
            avg(grid_import_w) AS grid_import_w,
            avg(grid_export_w) AS grid_export_w,
            avg(battery_soc_pct) AS battery_soc_pct,
            avg(battery_power_w) AS battery_power_w
        FROM energy_readings
        GROUP BY site_id, bucket
        WITH NO DATA
    """)
    op.execute("""
        SELECT add_continuous_aggregate_policy('energy_readings_5min',
            start_offset => INTERVAL '1 day',
            end_offset => INTERVAL '5 minutes',
            schedule_interval => INTERVAL '5 minutes',
            if_not_exists => TRUE)
    """)
    op.execute("""
        SELECT add_continuous_aggregate_policy('energy_readings_1hour',
            start_offset => INTERVAL '7 days',
            end_offset => INTERVAL '1 hour',
            schedule_interval => INTERVAL '1 hour',
            if_not_exists => TRUE)
    """)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("DROP MATERIALIZED VIEW IF EXISTS energy_readings_1hour CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS energy_readings_5min CASCADE")
