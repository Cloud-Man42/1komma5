from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from energy_core.db.models.base import Base

class HeartbeatSettingsModel(Base):
    __tablename__ = "heartbeat_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False, default=1)
    connection_type: Mapped[str] = mapped_column(String(16), nullable=False, default="mock")
    host: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    port: Mapped[int] = mapped_column(Integer, nullable=False, default=443)
    use_tls: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    api_path: Mapped[str] = mapped_column(String(128), nullable=False, default="/api")
    poll_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    dashboard_refresh_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    username: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    password: Mapped[str] = mapped_column("encrypted_password", Text, nullable=False, default="")
    api_token: Mapped[str] = mapped_column("encrypted_api_token", Text, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class HeartbeatDiscoveryRunModel(Base):
    __tablename__ = "heartbeat_discovery_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="COMPLETED")
    system_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    conclusion_class: Mapped[str | None] = mapped_column(String(8), nullable=True)
    bridge_lifecycle: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolved_ev_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    confidence_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    report_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    report_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class HeartbeatApiObservationModel(Base):
    __tablename__ = "heartbeat_api_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("heartbeat_discovery_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    observation_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    schema_fingerprint: Mapped[str | None] = mapped_column(String(32), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HeartbeatEvMappingModel(Base):
    __tablename__ = "heartbeat_ev_mappings"
    __table_args__ = (
        UniqueConstraint("site_id", "heartbeat_ev_id", name="uq_heartbeat_ev_mappings_site_ev"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    heartbeat_ev_id: Mapped[str] = mapped_column(String(128), nullable=False)
    heartbeat_ev_name: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    physical_charger_id: Mapped[int | None] = mapped_column(
        ForeignKey("ev_chargers.id", ondelete="SET NULL"), nullable=True
    )
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="heartbeat")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confidence_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    last_discovery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class HeartbeatBridgeSettingsModel(Base):
    __tablename__ = "heartbeat_bridge_settings"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    discovery_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    write_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    virtual_bridge_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    physical_control_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    soc_sync_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    replay_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    simulation_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    confidence_threshold_pct: Mapped[float] = mapped_column(Float, nullable=False, default=90.0)
    battery_priority_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="BATTERY_FIRST")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class HeartbeatWriteTestModel(Base):
    __tablename__ = "heartbeat_write_tests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    heartbeat_ev_id: Mapped[str] = mapped_column(String(128), nullable=False)
    classification: Mapped[str] = mapped_column(String(64), nullable=False)
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    steps_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    result_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
