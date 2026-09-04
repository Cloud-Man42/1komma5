"""EV smart-charging window recommendations (display / RECOMMEND mode)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from energy_core.db.models import EvChargerModel, SiteModel
from energy_core.flexible_load.ev_load import build_ev_orchestrated_load
from energy_core.price_engine.types import PricePeriod


@dataclass(frozen=True, slots=True)
class EvChargeRecommendation:
    charger_id: int
    charger_name: str
    window_start: datetime
    window_end: datetime
    avg_import_sek_kwh: float
    current_import_sek_kwh: float
    estimated_saving_sek: float | None
    reason: str
    reason_sv: str


def _as_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


def find_cheapest_charge_window(
    horizon: tuple[PricePeriod, ...],
    *,
    now: datetime,
    window_periods: int = 4,
    lookahead_hours: int = 18,
) -> tuple[datetime, datetime, float] | None:
    """Find lowest average import-price window (default 4×15 min = 1 h)."""
    if len(horizon) < window_periods:
        return None

    now = _as_utc(now)
    window_end_limit = now + timedelta(hours=lookahead_hours)
    future = [
        p
        for p in horizon
        if _as_utc(p.period_start) > now
        and _as_utc(p.period_start) <= window_end_limit
        and p.import_price_sek_kwh is not None
    ]
    if len(future) < window_periods:
        return None

    best: tuple[datetime, datetime, float] | None = None
    for idx in range(len(future) - window_periods + 1):
        chunk = future[idx : idx + window_periods]
        prices = [p.import_price_sek_kwh for p in chunk if p.import_price_sek_kwh is not None]
        if len(prices) < window_periods:
            continue
        avg = sum(prices) / len(prices)
        start = _as_utc(chunk[0].period_start)
        end = _as_utc(chunk[-1].period_end)
        if best is None or avg < best[2]:
            best = (start, end, avg)
    return best


def build_ev_recommendations(
    *,
    site: SiteModel,
    chargers: tuple[EvChargerModel, ...],
    horizon: tuple[PricePeriod, ...],
    current_import_sek_kwh: float | None,
    now: datetime | None = None,
    min_spread_sek_kwh: float = 0.08,
    energy_kwh: float = 10.0,
) -> tuple[EvChargeRecommendation, ...]:
    """Recommend cheapest import window for connected smart EV chargers."""
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    window = find_cheapest_charge_window(horizon, now=now)
    if window is None or current_import_sek_kwh is None:
        return ()

    window_start, window_end, avg_import = window
    if current_import_sek_kwh <= avg_import + min_spread_sek_kwh:
        return ()

    spread = current_import_sek_kwh - avg_import
    estimated_saving = round(spread * energy_kwh, 2) if spread > 0 else None
    start_local = _format_local_hhmm(window_start, site.timezone)
    end_local = _format_local_hhmm(window_end, site.timezone)

    recommendations: list[EvChargeRecommendation] = []
    for charger in chargers:
        if build_ev_orchestrated_load(charger, site, now=now) is None:
            continue
        recommendations.append(
            EvChargeRecommendation(
                charger_id=charger.id,
                charger_name=charger.name,
                window_start=window_start,
                window_end=window_end,
                avg_import_sek_kwh=round(avg_import, 4),
                current_import_sek_kwh=round(current_import_sek_kwh, 4),
                estimated_saving_sek=estimated_saving,
                reason=(
                    f"Cheaper import window {start_local}–{end_local} "
                    f"({avg_import:.2f} SEK/kWh vs now {current_import_sek_kwh:.2f}). "
                    "RECOMMEND mode — no automatic charger control."
                ),
                reason_sv=(
                    f"Billigare importfönster {start_local}–{end_local} "
                    f"({avg_import:.2f} kr/kWh jämfört med nu {current_import_sek_kwh:.2f}). "
                    "Rekommendation — ingen automatisk laddningsstyrning."
                ),
            )
        )
    return tuple(recommendations)


def _format_local_hhmm(ts: datetime, timezone: str) -> str:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return ts.astimezone(ZoneInfo(timezone)).strftime("%H:%M")
