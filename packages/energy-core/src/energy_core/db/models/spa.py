from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from energy_core.db.models.base import Base

class SpaDeviceConfigModel(Base):
    __tablename__ = "spa_device_config"

    consumer_id: Mapped[int] = mapped_column(
        ForeignKey("energy_consumers.id", ondelete="CASCADE"), primary_key=True
    )
    integration_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    api_base_url: Mapped[str] = mapped_column(String(255), nullable=False, default="https://api.myarcticspa.com")
    api_key: Mapped[str] = mapped_column("encrypted_api_key", Text, nullable=False, default="")
    external_spa_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    poll_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    energy_collection_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    cost_calculation_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    power_profiles_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    last_status_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    last_status_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SpaPollStateModel(Base):
    __tablename__ = "spa_poll_state"

    consumer_id: Mapped[int] = mapped_column(
        ForeignKey("energy_consumers.id", ondelete="CASCADE"), primary_key=True
    )
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_sample_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    backoff_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    polling_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class SpaControlConfigModel(Base):
    __tablename__ = "spa_control_config"

    consumer_id: Mapped[int] = mapped_column(
        ForeignKey("energy_consumers.id", ondelete="CASCADE"), primary_key=True
    )
    smart_control_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    strategy: Mapped[str] = mapped_column(String(32), nullable=False, default="SMART")
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    shadow_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    shadow_mode_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    min_cleaning_hours_per_day: Mapped[float] = mapped_column(Float, nullable=False, default=8.0)
    allowed_window_start: Mapped[str] = mapped_column(String(8), nullable=False, default="07:00")
    allowed_window_end: Mapped[str] = mapped_column(String(8), nullable=False, default="22:00")
    prefer_solar: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_battery: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    min_battery_soc_pct: Mapped[float] = mapped_column(Float, nullable=False, default=40.0)
    min_run_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=120)
    min_stop_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    max_starts_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    filter_cycles_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    filter_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=120)
    minimum_cycle_separation_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    filter_optimization_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_known_safe_filter_schedule_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    safety_floor_frequency_per_day: Mapped[float] = mapped_column(Float, nullable=False, default=4.0)
    safety_floor_duration_hours: Mapped[float] = mapped_column(Float, nullable=False, default=2.0)
    smart_preheat_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    normal_temperature_c: Mapped[float] = mapped_column(Float, nullable=False, default=38.0)
    max_preheat_temperature_c: Mapped[float] = mapped_column(Float, nullable=False, default=39.0)
    min_comfort_temperature_c: Mapped[float] = mapped_column(Float, nullable=False, default=37.0)
    load_priority: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    fixed_schedule_start: Mapped[str | None] = mapped_column(String(8), nullable=True)
    fixed_schedule_end: Mapped[str | None] = mapped_column(String(8), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class SpaEnergyEventModel(Base):
    __tablename__ = "spa_energy_event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    consumer_id: Mapped[int] = mapped_column(ForeignKey("energy_consumers.id", ondelete="CASCADE"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stop_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    runtime_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    solar_share: Mapped[float | None] = mapped_column(Float, nullable=True)
    battery_share: Mapped[float | None] = mapped_column(Float, nullable=True)
    grid_share: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    reason_sv: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    strategy: Mapped[str] = mapped_column(String(32), nullable=False, default="SMART")
    decision_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    manual_override: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    shadow: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class SpaActuatorStateModel(Base):
    __tablename__ = "spa_actuator_state"

    consumer_id: Mapped[int] = mapped_column(
        ForeignKey("energy_consumers.id", ondelete="CASCADE"), primary_key=True
    )
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="IDLE")
    runtime_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    integration_degraded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    integration_degraded_message_sv: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
