from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from energy_core.db.models.base import Base

class ChargingLocationModel(Base):
    __tablename__ = "charging_locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    classification: Mapped[str] = mapped_column(String(32), nullable=False, default="UNKNOWN")
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    radius_m: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    expected_operator: Mapped[str | None] = mapped_column(String(128), nullable=True)
    expected_network: Mapped[str | None] = mapped_column(String(128), nullable=True)
    expected_charging_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    charger_id: Mapped[int | None] = mapped_column(ForeignKey("ev_chargers.id", ondelete="SET NULL"), nullable=True)
    price_model: Mapped[str] = mapped_column(String(32), nullable=False, default="UNKNOWN")
    price_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ChargingStationModel(Base):
    __tablename__ = "charging_station"
    __table_args__ = (UniqueConstraint("provider", "provider_station_id", name="uq_charging_station_provider_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(16), nullable=False, default="CHARGEFINDER")
    provider_station_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    operator: Mapped[str | None] = mapped_column(String(128), nullable=True)
    station_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    address: Mapped[str | None] = mapped_column(String(256), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    country: Mapped[str | None] = mapped_column(String(8), nullable=True)
    connector_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    max_power_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    charging_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    external_station_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    network_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    times_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    user_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    raw_provider_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class ChargingStationLookupCacheModel(Base):
    __tablename__ = "charging_station_lookup_cache"

    geohash_key: Mapped[str] = mapped_column(String(12), primary_key=True)
    latitude_rounded: Mapped[float] = mapped_column(Float, nullable=False)
    longitude_rounded: Mapped[float] = mapped_column(Float, nullable=False)
    radius_m: Mapped[int] = mapped_column(Integer, nullable=False)
    resolved_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ChargeFinderIntegrationStatusModel(Base):
    __tablename__ = "chargefinder_integration_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_lookup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(String(512), nullable=True)
    cache_hits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cache_misses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    parser_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lookup_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    browser_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    parsing_version: Mapped[str] = mapped_column(String(16), nullable=False, default="1")


class ChargingLocationObservationModel(Base):
    __tablename__ = "charging_location_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    radius_m: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    location_name: Mapped[str] = mapped_column(String(128), nullable=False)
    charger_operator: Mapped[str | None] = mapped_column(String(128), nullable=True)
    charging_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
