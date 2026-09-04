"""Energy Opportunity Value — marginal kWh dispatch recommendations."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from energy_core.energy_optimizer.types import EnergyAction, EovConfig, EovDecision
from energy_core.price_engine.types import PricePeriod, PriceQuality, StrategyState


def _as_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


def _quality_confidence(quality: PriceQuality) -> float:
    return {
        PriceQuality.REAL: 0.82,
        PriceQuality.CALCULATED: 0.78,
        PriceQuality.ESTIMATED: 0.68,
        PriceQuality.STALE: 0.55,
        PriceQuality.MISSING: 0.35,
    }.get(quality, 0.5)


def _future_import_stats(
    periods: tuple[PricePeriod, ...],
    *,
    now: datetime,
    lookahead_hours: int,
) -> tuple[float | None, datetime | None]:
    window_end = now + timedelta(hours=lookahead_hours)
    best_price: float | None = None
    best_at: datetime | None = None
    for period in periods:
        start = _as_utc(period.period_start)
        if start <= now:
            continue
        if start > window_end:
            break
        price = period.import_price_sek_kwh
        if price is None:
            continue
        if best_price is None or price > best_price:
            best_price = price
            best_at = start
    return best_price, best_at


def _recommended_reserve(
    *,
    battery_soc_pct: float | None,
    peak_import: float | None,
    avg_import: float | None,
) -> float | None:
    if battery_soc_pct is None:
        return None
    if peak_import is None or avg_import is None:
        return max(25.0, min(60.0, battery_soc_pct))
    spread = peak_import - avg_import
    if spread <= 0.05:
        return 28.0
    if peak_import >= 2.5:
        return min(65.0, 40.0 + spread * 8.0)
    if peak_import >= 1.5:
        return min(55.0, 32.0 + spread * 6.0)
    return min(45.0, 28.0 + spread * 5.0)


def compute_eov_decision(
    *,
    current: PricePeriod | None,
    horizon: tuple[PricePeriod, ...],
    battery_soc_pct: float | None,
    config: EovConfig | None = None,
    now: datetime | None = None,
) -> EovDecision | None:
    """Recommend the best use of the next marginal kWh."""
    if current is None or current.import_price_sek_kwh is None:
        return None

    cfg = config or EovConfig()
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    import_now = current.import_price_sek_kwh
    export_now = current.export_price_sek_kwh or 0.0
    max_future_import, peak_at = _future_import_stats(
        horizon,
        now=now,
        lookahead_hours=cfg.lookahead_hours,
    )
    peak_import = max_future_import if max_future_import is not None else import_now

    store_future_value = peak_import * cfg.round_trip_efficiency - cfg.degradation_cost_sek_kwh
    store_net = store_future_value - max(export_now, import_now * 0.5)

    candidates: dict[EnergyAction, float] = {
        EnergyAction.USE_NOW: import_now,
        EnergyAction.EXPORT_TO_GRID: export_now,
        EnergyAction.STORE_IN_BATTERY: store_net,
        EnergyAction.WAIT: 0.0,
    }

    if battery_soc_pct is not None:
        if battery_soc_pct >= 96.0:
            candidates[EnergyAction.STORE_IN_BATTERY] = float("-inf")
        if battery_soc_pct <= 28.0:
            candidates[EnergyAction.DISCHARGE_BATTERY] = float("-inf")
        else:
            discharge_value = import_now - export_now
            if peak_import > import_now * 1.15:
                discharge_value = import_now
            candidates[EnergyAction.DISCHARGE_BATTERY] = discharge_value

    action = max(candidates, key=lambda key: candidates[key])
    expected_value = candidates[action]
    confidence = min(0.85, _quality_confidence(current.quality))

    strategy_state, reason, reason_sv = _map_action_to_strategy(
        action=action,
        import_now=import_now,
        export_now=export_now,
        peak_import=peak_import,
        peak_at=peak_at,
        battery_soc_pct=battery_soc_pct,
    )

    imports = [p.import_price_sek_kwh for p in horizon if p.import_price_sek_kwh is not None]
    avg_import = sum(imports) / len(imports) if imports else import_now

    return EovDecision(
        action=action,
        strategy_state=strategy_state,
        expected_value_sek_kwh=round(expected_value, 4),
        confidence=confidence,
        reason=reason,
        reason_sv=reason_sv,
        recommended_reserve_soc_pct=_recommended_reserve(
            battery_soc_pct=battery_soc_pct,
            peak_import=peak_import,
            avg_import=avg_import,
        ),
    )


def _map_action_to_strategy(
    *,
    action: EnergyAction,
    import_now: float,
    export_now: float,
    peak_import: float,
    peak_at: datetime | None,
    battery_soc_pct: float | None,
) -> tuple[StrategyState, str, str]:
    peak_label = peak_at.astimezone(UTC).strftime("%H:%M UTC") if peak_at else "later"

    if action == EnergyAction.STORE_IN_BATTERY:
        return (
            StrategyState.SAVE_BATTERY,
            (
                f"Storing energy beats export/use now (future import up to {peak_import:.2f} SEK/kWh "
                f"around {peak_label}). EOV recommendation — MONITOR_ONLY."
            ),
            (
                f"Lagra energi i batteriet lönar sig bättre än export/egenförbrukning nu "
                f"(import upp till {peak_import:.2f} kr/kWh ca {peak_label}). EOV-rekommendation."
            ),
        )
    if action == EnergyAction.EXPORT_TO_GRID:
        return (
            StrategyState.EXPORT,
            (
                f"Export at {export_now:.2f} SEK/kWh beats storing for future peaks. "
                "EOV recommendation — MONITOR_ONLY."
            ),
            (
                f"Exportera till {export_now:.2f} kr/kWh är bättre än att spara för kommande toppar. "
                "EOV-rekommendation."
            ),
        )
    if action == EnergyAction.DISCHARGE_BATTERY:
        return (
            StrategyState.DISCHARGE_BATTERY,
            (
                f"Discharge recommended: import {import_now:.2f} SEK/kWh, "
                f"peak ahead ~{peak_import:.2f} SEK/kWh."
            ),
            (
                f"Urladdning rekommenderas: import {import_now:.2f} kr/kWh, "
                f"topp väntas ~{peak_import:.2f} kr/kWh."
            ),
        )
    if action == EnergyAction.USE_NOW:
        if peak_import > import_now * 1.25:
            return (
                StrategyState.PEAK_AHEAD,
                (
                    f"Self-use now at {import_now:.2f} SEK/kWh; higher import expected later "
                    f"(~{peak_import:.2f} SEK/kWh)."
                ),
                (
                    f"Egenförbrukning nu ({import_now:.2f} kr/kWh); högre import väntas senare "
                    f"(~{peak_import:.2f} kr/kWh)."
                ),
            )
        return (
            StrategyState.NORMAL_SELF_USE,
            f"Self-use is optimal at {import_now:.2f} SEK/kWh versus export/store alternatives.",
            f"Egenförbrukning är optimal vid {import_now:.2f} kr/kWh jämfört med export/lagring.",
        )
    return (
        StrategyState.WAIT,
        "No clear economic advantage; holding position.",
        "Ingen tydlig ekonomisk fördel; avvakta.",
    )


def estimate_shiftable_savings(
    horizon: tuple[PricePeriod, ...],
    *,
    config: EovConfig | None = None,
) -> float | None:
    """Estimate daily savings from shifting load to cheapest import periods."""
    cfg = config or EovConfig()
    imports = [p.import_price_sek_kwh for p in horizon if p.import_price_sek_kwh is not None]
    if len(imports) < 4:
        return None
    avg = sum(imports) / len(imports)
    min_price = min(imports)
    spread = avg - min_price
    if spread <= 0:
        return 0.0
    return round(spread * cfg.shiftable_kwh_per_day, 2)
