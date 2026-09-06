from __future__ import annotations

from datetime import date, datetime
from typing import Any

from energy_core.integrations.heartbeat.connection import CLOUD_PORT, HeartbeatConnectionType
from pydantic import BaseModel, Field, field_validator

from app.schemas.sites import ReadingResponse


class AggregatedReadingResponse(BaseModel):
    bucket_start: datetime
    solar_production_w: float
    consumption_w: float
    grid_import_w: float
    grid_export_w: float
    battery_soc_pct: float
    battery_power_w: float


class HistoryResponse(BaseModel):
    slug: str
    bucket_minutes: int
    readings: list[ReadingResponse | AggregatedReadingResponse] = Field(default_factory=list)


class PeakReadingResponse(BaseModel):
    period_start: str
    solar_production_w: float
    consumption_w: float
    battery_charge_w: float
    battery_discharge_w: float


class PeaksResponse(BaseModel):
    slug: str
    timezone: str
    period: str
    peaks: list[PeakReadingResponse] = Field(default_factory=list)


class FinancialStatResponse(BaseModel):
    period_start: str
    solar_self_consumed_kwh: float
    battery_self_consumed_kwh: float
    exported_kwh: float
    imported_kwh: float
    solar_savings_sek: float
    battery_savings_sek: float
    export_revenue_sek: float
    grid_import_cost_sek: float
    market_priced_fraction: float
    energy_sale_revenue_sek: float = 0.0
    grid_benefit_revenue_sek: float = 0.0
    tax_credit_sek: float = 0.0
    effective_sell_price_sek_kwh: float | None = None
    export_spot_priced_fraction: float = 0.0
    uncontracted_exported_kwh: float = 0.0


class FinancialStatsResponse(BaseModel):
    slug: str
    timezone: str
    period: str
    fallback_purchase_price_sek_kwh: float
    export_compensation_sek_kwh: float
    sell_pricing_mode: str = "spot"
    sell_contract_start_date: date | None = None
    stats: list[FinancialStatResponse] = Field(default_factory=list)


class ForecastValuesResponse(BaseModel):
    solar_self_consumed_kwh: float
    battery_self_consumed_kwh: float
    exported_kwh: float
    imported_kwh: float
    solar_savings_sek: float
    battery_savings_sek: float
    export_revenue_sek: float
    grid_import_cost_sek: float
    net_sek: float


class MonthlyForecastResponse(BaseModel):
    month: str
    actual: ForecastValuesResponse
    forecast: ForecastValuesResponse
    total: ForecastValuesResponse


class YearForecastResponse(BaseModel):
    slug: str
    timezone: str
    year: int
    observed_days: int
    confidence: str
    uncertainty_pct: int
    import_baseline_year: int | None = None
    import_baseline_source: str | None = None
    import_baseline_estimated: bool = False
    import_baseline_kwh: float | None = None
    fallback_purchase_price_sek_kwh: float
    export_compensation_sek_kwh: float
    actual: ForecastValuesResponse
    forecast: ForecastValuesResponse
    total: ForecastValuesResponse
    months: list[MonthlyForecastResponse]


class HistoricalEnergyMonth(BaseModel):
    month: int = Field(ge=1, le=12)
    imported_kwh: float = Field(ge=0)
    imported_cost_sek: float | None = Field(default=None, ge=0)


class HistoricalEnergyYearUpdate(BaseModel):
    source: str = Field(default="", max_length=128)
    estimated: bool = False
    months: list[HistoricalEnergyMonth] = Field(min_length=12, max_length=12)


class HistoricalEnergyYearResponse(BaseModel):
    slug: str
    year: int
    source: str
    estimated: bool
    total_imported_kwh: float
    total_imported_cost_sek: float | None
    months: list[HistoricalEnergyMonth]


class MarketPricePointResponse(BaseModel):
    timestamp: datetime
    spot_eur_kwh: float
    all_in_eur_kwh: float | None = None
    spot_sek_kwh: float | None = None
    import_sek_kwh: float | None = None
    export_sek_kwh: float | None = None


class MarketPricesResponse(BaseModel):
    slug: str
    timezone: str
    resolution: str
    current_price_eur_kwh: float | None = None
    average_all_in_eur_kwh: float | None = None
    highest_all_in_eur_kwh: float | None = None
    lowest_all_in_eur_kwh: float | None = None
    current_spot_sek_kwh: float | None = None
    current_import_sek_kwh: float | None = None
    average_import_sek_kwh: float | None = None
    highest_import_sek_kwh: float | None = None
    lowest_import_sek_kwh: float | None = None
    points: list[MarketPricePointResponse] = Field(default_factory=list)
