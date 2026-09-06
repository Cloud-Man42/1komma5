from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from energy_core.db.models.base import Base

class EnergyConsumerModel(Base):
    __tablename__ = "energy_consumers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    consumer_type: Mapped[str] = mapped_column(String(32), nullable=False, default="SPA")
    name: Mapped[str] = mapped_column(String(128), nullable=False, default="Arctic Spa")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Europe/Stockholm")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ConsumerSampleModel(Base):
    __tablename__ = "consumer_samples"

    consumer_id: Mapped[int] = mapped_column(ForeignKey("energy_consumers.id", ondelete="CASCADE"), primary_key=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    power_w: Mapped[float | None] = mapped_column(Float, nullable=True)
    energy_delta_wh: Mapped[float | None] = mapped_column(Float, nullable=True)
    water_temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    set_temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    heater_active: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    pump_states_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    filter_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    spa_connected: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="ARCTIC_SPA_REST")
    quality: Mapped[str] = mapped_column(String(16), nullable=False, default="CALCULATED")
    component_breakdown_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class ConsumerIntervalModel(Base):
    __tablename__ = "consumer_intervals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    consumer_id: Mapped[int] = mapped_column(ForeignKey("energy_consumers.id", ondelete="CASCADE"), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    energy_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    average_power_w: Mapped[float | None] = mapped_column(Float, nullable=True)
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
    unknown_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    actual_cost_sek: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reference_cost_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    savings_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    heater_runtime_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pump_runtime_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    data_quality: Mapped[str | None] = mapped_column(String(16), nullable=True)


class ConsumerAggregateModel(Base):
    __tablename__ = "consumer_aggregates"

    __table_args__ = (
        UniqueConstraint("consumer_id", "granularity", "period_start", name="uq_consumer_aggregates_period"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    consumer_id: Mapped[int] = mapped_column(ForeignKey("energy_consumers.id", ondelete="CASCADE"), nullable=False)
    granularity: Mapped[str] = mapped_column(String(16), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    energy_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    solar_direct_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    solar_battery_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grid_battery_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grid_direct_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unknown_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    actual_cost_sek: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reference_cost_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    savings_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_power_w: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_power_w: Mapped[float | None] = mapped_column(Float, nullable=True)
    heater_runtime_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pump_runtime_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    measured_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    calculated_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    missing_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
