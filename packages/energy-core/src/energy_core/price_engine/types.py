"""Domain types for the EMIC price engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class PriceArea(StrEnum):
    SE4 = "SE4"
    DK2 = "DK2"


class Currency(StrEnum):
    SEK = "SEK"
    EUR = "EUR"


class PriceQuality(StrEnum):
    REAL = "REAL"
    CALCULATED = "CALCULATED"
    ESTIMATED = "ESTIMATED"
    STALE = "STALE"
    MISSING = "MISSING"


class PriceSource(StrEnum):
    HEARTBEAT = "heartbeat"
    REPLICATED_HOURLY = "replicated_hourly"
    NORD_POOL = "nord_pool"
    CACHE = "cache"
    FALLBACK = "fallback"


class OptimizationMode(StrEnum):
    MONITOR_ONLY = "MONITOR_ONLY"
    RECOMMEND = "RECOMMEND"
    SEMI_AUTOMATIC = "SEMI_AUTOMATIC"
    AUTOMATIC = "AUTOMATIC"


class StrategyState(StrEnum):
    NORMAL_SELF_USE = "NORMAL_SELF_USE"
    PEAK_AHEAD = "PEAK_AHEAD"
    SAVE_BATTERY = "SAVE_BATTERY"
    CHARGE_BATTERY = "CHARGE_BATTERY"
    DISCHARGE_BATTERY = "DISCHARGE_BATTERY"
    EXPORT = "EXPORT"
    CHARGE_VEHICLE = "CHARGE_VEHICLE"
    WAIT = "WAIT"
    PEAK_PROTECTION = "PEAK_PROTECTION"


INTERVAL_MINUTES = 15


@dataclass(frozen=True, slots=True)
class PricePeriod:
    period_start: datetime
    period_end: datetime
    site_id: int
    price_area: PriceArea
    currency: Currency
    market_price_sek_kwh: float | None
    import_price_sek_kwh: float | None
    export_price_sek_kwh: float | None
    source: PriceSource
    quality: PriceQuality
    is_estimated: bool
    components: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RawPricePoint:
    """Provider output before normalization to 15-minute periods."""

    timestamp: datetime
    market_price_eur_kwh: float | None = None
    import_price_eur_kwh: float | None = None
    export_price_eur_kwh: float | None = None
    native_resolution_minutes: int = 60
    components: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PriceEngineStatus:
    site_id: int
    last_market_refresh_at: datetime | None
    last_import_refresh_at: datetime | None
    last_export_refresh_at: datetime | None
    last_error: str | None
    missing_periods_count: int
    data_age_seconds: int | None
    optimization_mode: OptimizationMode
