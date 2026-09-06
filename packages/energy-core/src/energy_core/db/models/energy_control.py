from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from energy_core.db.models.base import Base

class EnergyForecastSnapshotModel(Base):
    __tablename__ = "energy_forecast_snapshots"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    forecast_kind: Mapped[str] = mapped_column(String(32), primary_key=True)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    predicted_value: Mapped[float] = mapped_column(Float, nullable=False)
    actual_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    forecast_recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actual_recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)


class EnergyControlActionModel(Base):
    __tablename__ = "energy_control_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    optimization_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    target: Mapped[str] = mapped_column(String(32), nullable=False, default="site")
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class AdminAuditLogModel(Base):
    __tablename__ = "admin_audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    http_method: Mapped[str] = mapped_column(String(16), nullable=False)
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    site_slug: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class FlexibleLoadPlanModel(Base):
    __tablename__ = "flexible_load_plan"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    consumer_id: Mapped[int | None] = mapped_column(ForeignKey("energy_consumers.id", ondelete="SET NULL"), nullable=True)
    load_id: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    reason_sv: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    explanation_sv: Mapped[str] = mapped_column(Text, nullable=False, default="")
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expected_energy_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_cost_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_cost_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    savings_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_energy_source: Mapped[str | None] = mapped_column(String(16), nullable=True)
    fallback_from_solar_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    windows_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class FlexibleLoadPlanBlockModel(Base):
    __tablename__ = "flexible_load_plan_block"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("flexible_load_plan.id", ondelete="CASCADE"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    solar_forecast_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    house_load_forecast_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    available_surplus_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    marginal_cost_sek_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    expected_energy_source: Mapped[str] = mapped_column(String(16), nullable=False, default="GRID")
    price_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
