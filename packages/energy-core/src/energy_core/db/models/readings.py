from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from energy_core.db.models.base import Base

class EnergyReadingModel(Base):
    __tablename__ = "energy_readings"

    tenant_id: Mapped[int | None] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    solar_production_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    consumption_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grid_import_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grid_export_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    battery_soc_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    battery_power_w: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    ev_power_w: Mapped[float | None] = mapped_column(Float, nullable=True)
    battery_charge_w: Mapped[float | None] = mapped_column(Float, nullable=True)
    battery_discharge_w: Mapped[float | None] = mapped_column(Float, nullable=True)

    site: Mapped[SiteModel] = relationship(back_populates="readings")


class EnergyHourlyModel(Base):
    __tablename__ = "energy_hourly"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    hour: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    solar_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    consumption_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    import_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    export_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


class EnergyDailyModel(Base):
    __tablename__ = "energy_daily"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    solar_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    consumption_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    import_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    export_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    import_cost_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    export_revenue_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
