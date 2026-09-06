from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from energy_core.db.models.base import Base

class VehicleProviderConnectionModel(Base):
    __tablename__ = "vehicle_provider_connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="mercedes")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    region: Mapped[str] = mapped_column(String(32), nullable=False, default="Europe")
    username: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    encrypted_password: Mapped[str] = mapped_column(Text, nullable=False, default="")
    encrypted_access_token: Mapped[str] = mapped_column(Text, nullable=False, default="")
    encrypted_refresh_token: Mapped[str] = mapped_column(Text, nullable=False, default="")
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    device_guid: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    connection_state: Mapped[str] = mapped_column(String(32), nullable=False, default="DISCONNECTED")
    commands_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_error: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    backoff_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    blocked_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reconnect_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    http_429_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    decode_failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_token_refresh_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_polling_interval_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class VehicleModel(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="mercedes")
    external_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    vin: Mapped[str | None] = mapped_column(String(32), nullable=True)
    manufacturer: Mapped[str] = mapped_column(String(64), nullable=False, default="Mercedes-Benz")
    model: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    display_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    charger_id: Mapped[int | None] = mapped_column(ForeignKey("ev_chargers.id", ondelete="SET NULL"), nullable=True)
    usable_battery_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class VehicleCapabilityModel(Base):
    __tablename__ = "vehicle_capabilities"

    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), primary_key=True)
    capability: Mapped[str] = mapped_column(String(64), primary_key=True)
    available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="discovery")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class VehicleStateLatestModel(Base):
    __tablename__ = "vehicle_state_latest"

    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), primary_key=True)
    state_of_charge_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_soc_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    electric_range_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_plugged_in: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_charging: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    charging_power_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    charging_power_limit_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_charge_complete_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    departure_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    soc_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    charging_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    range_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    connection_state: Mapped[str] = mapped_column(String(32), nullable=False, default="DISCONNECTED")
    data_quality: Mapped[str] = mapped_column(String(16), nullable=False, default="UNKNOWN")
    last_vehicle_update: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_provider_update: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class VehicleStateHistoryModel(Base):
    __tablename__ = "vehicle_state_history"

    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), primary_key=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    state_of_charge_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_soc_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    electric_range_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_plugged_in: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_charging: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    charging_power_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    connection_state: Mapped[str] = mapped_column(String(32), nullable=False, default="DISCONNECTED")
    data_quality: Mapped[str] = mapped_column(String(16), nullable=False, default="UNKNOWN")


class VehicleHaloCorrelationModel(Base):
    __tablename__ = "vehicle_halo_correlation"

    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), primary_key=True)
    charger_id: Mapped[int | None] = mapped_column(ForeignKey("ev_chargers.id", ondelete="SET NULL"), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="UNAVAILABLE")
    plugged_agreement: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    charging_agreement: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    power_delta_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    vehicle_power_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    halo_power_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class VehicleChargeSessionModel(Base):
    __tablename__ = "vehicle_charge_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    charger_id: Mapped[int | None] = mapped_column(ForeignKey("ev_chargers.id", ondelete="CASCADE"), nullable=True, index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    ev_charging_session_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    disconnected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    charging_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    charging_stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    start_soc: Mapped[float | None] = mapped_column(Float, nullable=True)
    end_soc: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_soc: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    meter_start_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    meter_stop_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    halo_energy_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_battery_energy_delta_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    solar_direct_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    solar_battery_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    grid_battery_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    grid_direct_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_cost_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    reference_cost_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    savings_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    renewable_share_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    grid_share_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    identification_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    energy_quality: Mapped[str | None] = mapped_column(String(16), nullable=True)
    cost_quality: Mapped[str | None] = mapped_column(String(16), nullable=True)
    attribution_quality: Mapped[str | None] = mapped_column(String(16), nullable=True)
    savings_baseline: Mapped[str] = mapped_column(String(32), nullable=False, default="IMMEDIATE_GRID_CHARGING")
    calculation_version: Mapped[str] = mapped_column(String(32), nullable=False, default="vehicle-charge-v1")
    reconciliation_delta_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    reconciliation_note: Mapped[str | None] = mapped_column(String(128), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    location_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    charger_operator: Mapped[str | None] = mapped_column(String(128), nullable=True)
    charger_network: Mapped[str | None] = mapped_column(String(128), nullable=True)
    charging_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    connector_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    home_charging: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    energy_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    estimated_energy_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    charging_power_avg_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    charging_power_max_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    charging_cost_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    price_model: Mapped[str | None] = mapped_column(String(32), nullable=True)
    price_value_sek_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    detection_confidence: Mapped[str | None] = mapped_column(String(16), nullable=True)
    identification_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vehicle_data_quality: Mapped[str | None] = mapped_column(String(16), nullable=True)
    charging_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    charging_station_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    station_provider: Mapped[str | None] = mapped_column(String(16), nullable=True)
    station_provider_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    station_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    distance_from_vehicle_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    station_confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    station_resolution_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    station_candidates_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    intervals: Mapped[list["VehicleChargingIntervalModel"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )


class VehicleChargingIntervalModel(Base):
    __tablename__ = "vehicle_charging_intervals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("vehicle_charge_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    charger_id: Mapped[int] = mapped_column(ForeignKey("ev_chargers.id", ondelete="CASCADE"), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    charged_energy_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    average_charging_power_w: Mapped[float | None] = mapped_column(Float, nullable=True)
    pv_production_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    house_consumption_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    grid_import_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    grid_export_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    battery_charge_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    battery_discharge_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    electricity_price_sek_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    solar_direct_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    solar_battery_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grid_battery_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grid_direct_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    actual_cost_sek: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reference_cost_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    savings_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    data_quality: Mapped[str | None] = mapped_column(String(16), nullable=True)

    session: Mapped[VehicleChargeSessionModel] = relationship(back_populates="intervals")


class VehicleAttributeObservationModel(Base):
    __tablename__ = "vehicle_attribute_observations"
    __table_args__ = (
        UniqueConstraint(
            "vehicle_id",
            "attribute_name",
            "source",
            name="uq_vehicle_attribute_obs_vehicle_name_source",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    attribute_name: Mapped[str] = mapped_column(String(128), nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="WS")
    value_type: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    masked_sample: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class VehicleApiEventModel(Base):
    __tablename__ = "vehicle_api_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    connection_id: Mapped[int] = mapped_column(
        ForeignKey("vehicle_provider_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    endpoint: Mapped[str] = mapped_column(String(512), nullable=False)
    method: Mapped[str] = mapped_column(String(16), nullable=False, default="GET")
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class VehicleIntegrationEventModel(Base):
    __tablename__ = "vehicle_integration_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="INFO")
    message: Mapped[str] = mapped_column(String(512), nullable=False)
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
