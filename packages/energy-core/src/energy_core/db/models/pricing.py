from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from energy_core.db.models.base import Base

class MarketPriceModel(Base):
    __tablename__ = "market_prices"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    spot_price_eur_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    all_in_price_eur_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    feed_in_price_eur_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)

    site: Mapped[SiteModel] = relationship(back_populates="market_prices")


class PricePeriodModel(Base):
    __tablename__ = "price_periods"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    price_area: Mapped[str] = mapped_column(String(8), nullable=False, default="SE4")
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="SEK")
    market_price_sek_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    import_price_sek_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    export_price_sek_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="heartbeat")
    quality: Mapped[str] = mapped_column(String(16), nullable=False, default="REAL")
    is_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    components_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    site: Mapped[SiteModel] = relationship(back_populates="price_periods")


class PriceEngineStateModel(Base):
    __tablename__ = "price_engine_state"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    last_market_refresh_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_import_refresh_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_export_refresh_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_periods_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    data_age_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    optimization_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="MONITOR_ONLY")


class FinancialDailyModel(Base):
    __tablename__ = "financial_daily"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    solar_self_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    battery_self_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    export_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    import_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    solar_savings_sek: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    battery_savings_sek: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grid_import_cost_sek: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    market_priced_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    priced_denominator_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    energy_sale_sek: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grid_benefit_sek: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    spot_priced_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fallback_priced_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    negative_price_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    contracted_export_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    uncontracted_export_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
