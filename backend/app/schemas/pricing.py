from __future__ import annotations

from datetime import date, datetime
from typing import Any

from energy_core.integrations.heartbeat.connection import CLOUD_PORT, HeartbeatConnectionType
from pydantic import BaseModel, Field, field_validator

class PricePeriodResponse(BaseModel):
    period_start: datetime
    period_end: datetime
    price_area: str
    currency: str
    market_price_sek_kwh: float | None = None
    import_price_sek_kwh: float | None = None
    export_price_sek_kwh: float | None = None
    source: str
    quality: str
    is_estimated: bool
    components: dict = Field(default_factory=dict)


class PriceEngineCurrentResponse(BaseModel):
    slug: str
    timezone: str
    period: PricePeriodResponse | None = None


class PriceEngineDayResponse(BaseModel):
    slug: str
    timezone: str
    day: date
    periods: list[PricePeriodResponse] = Field(default_factory=list)


class PriceEngineRangeResponse(BaseModel):
    slug: str
    timezone: str
    from_time: datetime
    to_time: datetime
    periods: list[PricePeriodResponse] = Field(default_factory=list)


class PriceEngineStatusResponse(BaseModel):
    slug: str
    last_market_refresh_at: datetime | None = None
    last_import_refresh_at: datetime | None = None
    last_export_refresh_at: datetime | None = None
    last_error: str | None = None
    missing_periods_count: int = 0
    data_age_seconds: int | None = None
    optimization_mode: str = "MONITOR_ONLY"


class EvRecommendationResponse(BaseModel):
    charger_id: int
    charger_name: str
    window_start: datetime
    window_end: datetime
    avg_import_sek_kwh: float
    current_import_sek_kwh: float
    estimated_saving_sek: float | None = None
    reason_sv: str


class EnergyStrategyCurrentResponse(BaseModel):
    slug: str
    timezone: str
    period_start: datetime
    market_price_sek_kwh: float | None = None
    import_price_sek_kwh: float | None = None
    export_price_sek_kwh: float | None = None
    market_quality: str
    import_quality: str
    export_quality: str
    battery_soc_pct: float | None = None
    strategy_state: str
    confidence: float
    reason: str
    reason_sv: str
    next_peak_at: datetime | None = None
    next_peak_import_sek_kwh: float | None = None
    optimization_mode: str
    expected_saving_today_sek: float | None = None
    recommended_reserve_soc_pct: float | None = None
    recommended_action: str | None = None
    eov_value_sek_kwh: float | None = None
    grid_surcharge_sek_kwh: float | None = None
    fuse_headroom_a: float | None = None
    fuse_utilization_pct: float | None = None
    ev_recommendations: list[EvRecommendationResponse] = Field(default_factory=list)
