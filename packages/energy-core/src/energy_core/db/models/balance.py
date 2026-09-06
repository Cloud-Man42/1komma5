from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from energy_core.db.models.base import Base

class BatteryEnergyLedgerModel(Base):
    __tablename__ = "battery_energy_ledger"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    solar_energy_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grid_energy_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grid_energy_cost_sek: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


class HistoricalMonthlyEnergyModel(Base):
    __tablename__ = "historical_monthly_energy"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    month: Mapped[int] = mapped_column(Integer, primary_key=True)
    imported_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    imported_cost_sek: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    site: Mapped[SiteModel] = relationship(back_populates="historical_monthly_energy")


class EnergyBalanceSnapshotModel(Base):
    __tablename__ = "energy_balance_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    charger_id: Mapped[int] = mapped_column(ForeignKey("ev_chargers.id", ondelete="CASCADE"), nullable=False, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    flags_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
