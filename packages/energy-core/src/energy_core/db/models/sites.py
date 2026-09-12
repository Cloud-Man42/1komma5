from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from energy_core.db.models.base import Base

class SiteModel(Base):
    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    external_system_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    heartbeat_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("heartbeat_accounts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    heartbeat_site_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    heartbeat_system_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    heartbeat_asset_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    heartbeat_device_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    heartbeat_serial_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    heartbeat_gateway_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    fallback_purchase_price_sek_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=2.0)
    export_compensation_sek_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)
    energy_economics_country: Mapped[str] = mapped_column(String(8), nullable=False, default="SE")
    sell_pricing_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="spot")
    sell_provider: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    sell_adjustment_ore_per_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sell_deduction_ore_per_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grid_benefit_ore_per_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    historical_tax_credit_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sell_contract_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    main_fuse_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    safety_margin_a: Mapped[float] = mapped_column(Float, nullable=False, default=2.0)
    price_area: Mapped[str] = mapped_column(String(8), nullable=False, default="SE4")
    optimization_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="MONITOR_ONLY")
    energy_control_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    battery_usable_capacity_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)

    readings: Mapped[list["EnergyReadingModel"]] = relationship(back_populates="site")
    market_prices: Mapped[list["MarketPriceModel"]] = relationship(
        back_populates="site",
        cascade="all, delete-orphan",
    )
    price_periods: Mapped[list["PricePeriodModel"]] = relationship(
        back_populates="site",
        cascade="all, delete-orphan",
    )
    historical_monthly_energy: Mapped[list["HistoricalMonthlyEnergyModel"]] = relationship(
        back_populates="site",
        cascade="all, delete-orphan",
    )
    ev_chargers: Mapped[list["EvChargerModel"]] = relationship(
        back_populates="site",
        cascade="all, delete-orphan",
    )
    solar_configuration: Mapped["SolarSiteConfigurationModel | None"] = relationship(
        back_populates="site",
        cascade="all, delete-orphan",
        uselist=False,
    )


class SiteEnergyConfigModel(Base):
    __tablename__ = "site_energy_config"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    load_includes_ev_charger: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    inverter_display_name: Mapped[str] = mapped_column(
        String(128), nullable=False, default="Sungrow Hybrid Inverter SH10"
    )
    physical_ev_charger_label: Mapped[str] = mapped_column(String(128), nullable=False, default="Charge Amps Halo")
    ev_vehicle_label: Mapped[str] = mapped_column(String(128), nullable=False, default="Mercedes EQE 500")


class SiteLiveSnapshotModel(Base):
    __tablename__ = "site_live_snapshots"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    freshness: Mapped[str] = mapped_column(String(16), nullable=False, default="DEGRADED")
    source_status_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
