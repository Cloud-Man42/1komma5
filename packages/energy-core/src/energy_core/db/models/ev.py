from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from energy_core.db.models.base import Base

class EvChargerModel(Base):
    __tablename__ = "ev_chargers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(64), nullable=False, default="ChargeAmps")
    model: Mapped[str] = mapped_column(String(64), nullable=False, default="Halo")
    control_source: Mapped[str] = mapped_column(String(16), nullable=False, default="chargeamp")
    heartbeat_ev_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    heartbeat_charger_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    chargeamp_charger_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    manufacturer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    integration_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    external_charger_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    connection_settings: Mapped[str | None] = mapped_column(Text, nullable=True)
    connection_status: Mapped[str] = mapped_column(String(32), nullable=False, default="NOT_CONFIGURED")
    last_connection_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_connection_test_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    bridge_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    max_current_a: Mapped[float] = mapped_column(Float, nullable=False, default=16.0)
    min_current_a: Mapped[float] = mapped_column(Float, nullable=False, default=6.0)
    phases: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    nominal_voltage_v: Mapped[float] = mapped_column(Float, nullable=False, default=230.0)
    max_power_w: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_grid_import_w: Mapped[float | None] = mapped_column(Float, nullable=True)
    update_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    min_change_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    current_hysteresis_a: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    stale_timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=120)
    chargeamps_api_key: Mapped[str] = mapped_column("encrypted_chargeamps_api_key", Text, nullable=False, default="")
    last_applied_current_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_bridge_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat_data_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    override_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    charging_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    departure_time: Mapped[str | None] = mapped_column(String(8), nullable=True)
    target_soc_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    load_priority: Mapped[int] = mapped_column(Integer, nullable=False, default=40)
    solar_start_threshold_w: Mapped[float] = mapped_column(Float, nullable=False, default=1000.0)
    solar_stop_threshold_w: Mapped[float] = mapped_column(Float, nullable=False, default=600.0)
    solar_start_delay_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    solar_stop_delay_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    last_charging_action: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_charging_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_charger_error_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_halo_connected: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_vehicle_connected: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    smart_charging_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_requested_current_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_configured_current_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_actual_charging_current_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_actual_power_w: Mapped[float | None] = mapped_column(Float, nullable=True)
    externally_limited: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_stop_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    start_delay_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=120)
    stop_delay_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    minimum_run_time_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    minimum_off_time_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    temporary_grid_import_allowance_w: Mapped[float] = mapped_column(Float, nullable=False, default=800.0)
    temporary_grid_import_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=180)
    grid_deadband_w: Mapped[float] = mapped_column(Float, nullable=False, default=300.0)
    minimum_current_change_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    max_current_increase_per_step_a: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    max_current_decrease_per_step_a: Mapped[float] = mapped_column(Float, nullable=False, default=2.0)
    max_automatic_starts_per_hour: Mapped[int] = mapped_column(Integer, nullable=False, default=4)

    virtual_evse_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    semp_device_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    semp_endpoint_registered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    site: Mapped[SiteModel] = relationship(back_populates="ev_chargers")
    bridge_cycles: Mapped[list["EvBridgeCycleModel"]] = relationship(
        back_populates="charger",
        cascade="all, delete-orphan",
    )
    charging_sessions: Mapped[list["EvChargingSessionModel"]] = relationship(
        back_populates="charger",
        cascade="all, delete-orphan",
    )


class EvChargingSessionModel(Base):
    __tablename__ = "ev_charging_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    charger_id: Mapped[int] = mapped_column(ForeignKey("ev_chargers.id", ondelete="CASCADE"), nullable=False, index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    meter_start_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    meter_stop_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_energy_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    solar_direct_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    solar_battery_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    grid_battery_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    grid_direct_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_cost_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    reference_cost_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    savings_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    smart_charging_savings_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    solar_contribution_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    renewable_share_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    grid_share_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    energy_quality: Mapped[str | None] = mapped_column(String(16), nullable=True)
    cost_quality: Mapped[str | None] = mapped_column(String(16), nullable=True)
    attribution_quality: Mapped[str | None] = mapped_column(String(16), nullable=True)
    savings_baseline: Mapped[str] = mapped_column(String(32), nullable=False, default="IMMEDIATE_GRID_CHARGING")
    calculation_version: Mapped[str] = mapped_column(String(32), nullable=False, default="ev-energy-v1")
    reconciliation_delta_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    reconciliation_note: Mapped[str | None] = mapped_column(String(128), nullable=True)
    chargeamps_session_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    charger: Mapped[EvChargerModel] = relationship(back_populates="charging_sessions")
    intervals: Mapped[list["EvChargingIntervalModel"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )


class EvChargingIntervalModel(Base):
    __tablename__ = "ev_charging_intervals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("ev_charging_sessions.id", ondelete="CASCADE"), nullable=False)
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

    session: Mapped[EvChargingSessionModel] = relationship(back_populates="intervals")


class EvBridgeCycleModel(Base):
    __tablename__ = "ev_bridge_cycles"

    charger_id: Mapped[int] = mapped_column(ForeignKey("ev_chargers.id", ondelete="CASCADE"), primary_key=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    applied_current_a: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    price_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    policy_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    decision_reason: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    override_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    vehicle_connected: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    charger: Mapped[EvChargerModel] = relationship(back_populates="bridge_cycles")


class VirtualChargerDecisionModel(Base):
    __tablename__ = "virtual_charger_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    charger_id: Mapped[int | None] = mapped_column(ForeignKey("ev_chargers.id", ondelete="SET NULL"), nullable=True)
    heartbeat_ev_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    bridge_state: Mapped[str] = mapped_column(String(64), nullable=False)
    heartbeat_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ai_decision: Mapped[str | None] = mapped_column(String(128), nullable=True)
    decision_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    reason: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class VirtualChargerCommandModel(Base):
    __tablename__ = "virtual_charger_commands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    charger_id: Mapped[int | None] = mapped_column(ForeignKey("ev_chargers.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    current_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    simulated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class VirtualChargerReplayRunModel(Base):
    __tablename__ = "virtual_charger_replay_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    report_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    report_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
