"""Solar forecast v2 tables."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "021_solar_forecast_v2"
down_revision = "020_solar_forecast_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "solar_forecast_observations",
        sa.Column(
            "site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("forecast_date", sa.Date(), primary_key=True),
        sa.Column("forecast_generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("forecast_kwh_raw", sa.Float(), nullable=True),
        sa.Column("forecast_kwh_corrected", sa.Float(), nullable=True),
        sa.Column("actual_kwh", sa.Float(), nullable=True),
        sa.Column("weather_provider", sa.String(length=32), nullable=True),
        sa.Column("weather_model", sa.String(length=32), nullable=True),
        sa.Column("cloud_cover_avg", sa.Float(), nullable=True),
        sa.Column("cloud_cover_hourly_json", sa.Text(), nullable=True),
        sa.Column("solar_radiation", sa.Float(), nullable=True),
        sa.Column("temperature_avg", sa.Float(), nullable=True),
        sa.Column("precipitation", sa.Float(), nullable=True),
        sa.Column("sunshine_duration", sa.Float(), nullable=True),
        sa.Column("sunrise", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sunset", sa.DateTime(timezone=True), nullable=True),
        sa.Column("weather_condition_bucket", sa.String(length=32), nullable=True),
        sa.Column("correction_factor_used", sa.Float(), nullable=True),
        sa.Column("absolute_error_kwh", sa.Float(), nullable=True),
        sa.Column("percentage_error", sa.Float(), nullable=True),
        sa.Column("signed_error_kwh", sa.Float(), nullable=True),
        sa.Column("raw_absolute_error_kwh", sa.Float(), nullable=True),
        sa.Column("raw_percentage_error", sa.Float(), nullable=True),
        sa.Column("data_completeness_pct", sa.Float(), nullable=True),
        sa.Column("training_eligible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("exclusion_reason", sa.String(length=64), nullable=True),
        sa.Column(
            "model_version",
            sa.String(length=32),
            nullable=False,
            server_default="solar-forecast-v2",
        ),
        sa.Column("site_configuration_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "solar_forecast_model_profiles",
        sa.Column(
            "site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column(
            "model_version",
            sa.String(length=32),
            nullable=False,
            server_default="solar-forecast-v2",
        ),
        sa.Column("historical_samples", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("model_state", sa.String(length=32), nullable=False, server_default="NO_DATA"),
        sa.Column("mape_7d", sa.Float(), nullable=True),
        sa.Column("mape_30d", sa.Float(), nullable=True),
        sa.Column("mape_90d", sa.Float(), nullable=True),
        sa.Column("mape_7d_valid_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mape_30d_valid_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mape_90d_valid_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mae_7d", sa.Float(), nullable=True),
        sa.Column("mae_30d", sa.Float(), nullable=True),
        sa.Column("mae_90d", sa.Float(), nullable=True),
        sa.Column("bias_7d", sa.Float(), nullable=True),
        sa.Column("bias_30d", sa.Float(), nullable=True),
        sa.Column("bias_90d", sa.Float(), nullable=True),
        sa.Column("raw_mae_30d", sa.Float(), nullable=True),
        sa.Column("corrected_mae_30d", sa.Float(), nullable=True),
        sa.Column("improvement_pct_30d", sa.Float(), nullable=True),
        sa.Column("correction_factor", sa.Float(), nullable=False, server_default="1"),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("seasonal_factors_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("last_training_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_evaluation_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "solar_arrays",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("name", sa.String(length=128), nullable=False, server_default="Main"),
        sa.Column("capacity_kwp", sa.Float(), nullable=False),
        sa.Column("azimuth_degrees", sa.Float(), nullable=False, server_default="180"),
        sa.Column("tilt_degrees", sa.Float(), nullable=False, server_default="35"),
    )
    op.create_index("ix_solar_arrays_site_id", "solar_arrays", ["site_id"])
    op.create_table(
        "solar_site_configuration_versions",
        sa.Column(
            "site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("version", sa.Integer(), primary_key=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("config_snapshot_json", sa.Text(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_table("solar_site_configuration_versions")
    op.drop_index("ix_solar_arrays_site_id", table_name="solar_arrays")
    op.drop_table("solar_arrays")
    op.drop_table("solar_forecast_model_profiles")
    op.drop_table("solar_forecast_observations")
