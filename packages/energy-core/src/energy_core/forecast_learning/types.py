"""Forecast learning types."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ForecastKind(str, Enum):
    IMPORT_PRICE_SEK_KWH = "import_price_sek_kwh"
    LOAD_W = "load_w"
    SOLAR_W = "solar_w"


@dataclass(frozen=True, slots=True)
class ForecastSnapshot:
    period_start: datetime
    period_end: datetime
    kind: ForecastKind
    predicted_value: float
    actual_value: float | None
    forecast_recorded_at: datetime
    actual_recorded_at: datetime | None
    model_version: str | None = None


@dataclass(frozen=True, slots=True)
class ForecastMetricSummary:
    kind: ForecastKind
    mae: float | None
    bias: float | None
    sample_count: int
    mape_pct: float | None


@dataclass(frozen=True, slots=True)
class ForecastLearningSummary:
    site_id: int
    days: int
    metrics: tuple[ForecastMetricSummary, ...]
    last_reconciled_at: datetime | None
