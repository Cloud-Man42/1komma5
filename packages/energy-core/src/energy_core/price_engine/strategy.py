"""Energy strategy powered by EOV optimizer (Phase 2) + EV/tariff hints (Phase 3)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from energy_core.energy_optimizer.eov import compute_eov_decision, estimate_shiftable_savings
from energy_core.energy_optimizer.types import EovConfig, EovDecision
from energy_core.price_engine.ev_recommendations import EvChargeRecommendation
from energy_core.price_engine.peak_protection import PeakProtectionHint
from energy_core.price_engine.periods import current_period_start
from energy_core.price_engine.tariff import TariffBreakdown, tariff_breakdown_from_period
from energy_core.price_engine.types import OptimizationMode, PricePeriod, PriceQuality, StrategyState


def _as_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class EvRecommendationSnapshot:
    charger_id: int
    charger_name: str
    window_start: datetime
    window_end: datetime
    avg_import_sek_kwh: float
    current_import_sek_kwh: float
    estimated_saving_sek: float | None
    reason_sv: str


@dataclass(frozen=True, slots=True)
class EnergyStrategySnapshot:
    site_slug: str
    period_start: datetime
    market_price_sek_kwh: float | None
    import_price_sek_kwh: float | None
    export_price_sek_kwh: float | None
    market_quality: PriceQuality
    import_quality: PriceQuality
    export_quality: PriceQuality
    battery_soc_pct: float | None
    strategy_state: StrategyState
    confidence: float
    reason: str
    reason_sv: str
    next_peak_at: datetime | None
    next_peak_import_sek_kwh: float | None
    optimization_mode: OptimizationMode
    expected_saving_today_sek: float | None
    recommended_reserve_soc_pct: float | None
    recommended_action: str | None = None
    eov_value_sek_kwh: float | None = None
    grid_surcharge_sek_kwh: float | None = None
    fuse_headroom_a: float | None = None
    fuse_utilization_pct: float | None = None
    ev_recommendations: tuple[EvRecommendationSnapshot, ...] = ()


def build_strategy_snapshot(
    *,
    site_slug: str,
    timezone: str,
    current: PricePeriod | None,
    horizon: tuple[PricePeriod, ...],
    battery_soc_pct: float | None,
    optimization_mode: OptimizationMode = OptimizationMode.MONITOR_ONLY,
    eov_config: EovConfig | None = None,
    peak_hint: PeakProtectionHint | None = None,
    ev_recommendations: tuple[EvChargeRecommendation, ...] = (),
    now: datetime | None = None,
) -> EnergyStrategySnapshot:
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    period_start = current.period_start if current else current_period_start(timezone=timezone, now=now)

    market = current.market_price_sek_kwh if current else None
    import_price = current.import_price_sek_kwh if current else None
    export_price = current.export_price_sek_kwh if current else None
    tariff: TariffBreakdown | None = tariff_breakdown_from_period(current)

    future = tuple(p for p in horizon if _as_utc(p.period_start) > now)
    peak = _find_import_peak(future)

    eov = compute_eov_decision(
        current=current,
        horizon=horizon,
        battery_soc_pct=battery_soc_pct,
        config=eov_config,
        now=now,
    )

    if eov is not None:
        state = eov.strategy_state
        confidence = eov.confidence
        reason = eov.reason
        reason_sv = eov.reason_sv
        reserve = eov.recommended_reserve_soc_pct
        recommended_action = eov.action.value
        eov_value = eov.expected_value_sek_kwh
    else:
        state, confidence, reason, reason_sv = _heuristic_state(
            current_import=import_price,
            peak_import=peak[1] if peak else None,
            export_price=export_price,
        )
        reserve = _recommended_reserve(battery_soc_pct, peak[1] if peak else None)
        recommended_action = None
        eov_value = None

    ev_snaps = tuple(
        EvRecommendationSnapshot(
            charger_id=rec.charger_id,
            charger_name=rec.charger_name,
            window_start=rec.window_start,
            window_end=rec.window_end,
            avg_import_sek_kwh=rec.avg_import_sek_kwh,
            current_import_sek_kwh=rec.current_import_sek_kwh,
            estimated_saving_sek=rec.estimated_saving_sek,
            reason_sv=rec.reason_sv,
        )
        for rec in ev_recommendations
    )

    if peak_hint is not None:
        state = StrategyState.PEAK_PROTECTION
        confidence = min(confidence, 0.78)
        reason = peak_hint.reason
        reason_sv = peak_hint.reason_sv
    elif ev_snaps and optimization_mode in {OptimizationMode.MONITOR_ONLY, OptimizationMode.RECOMMEND}:
        best = ev_snaps[0]
        state = StrategyState.CHARGE_VEHICLE
        confidence = min(max(confidence, 0.72), 0.82)
        start_local = _format_local_hhmm(best.window_start, timezone)
        end_local = _format_local_hhmm(best.window_end, timezone)
        reason = (
            f"EV charging recommended {start_local}–{end_local} "
            f"local at ~{best.avg_import_sek_kwh:.2f} SEK/kWh."
        )
        reason_sv = (
            f"EV-laddning rekommenderas {start_local}–{end_local} "
            f"till ~{best.avg_import_sek_kwh:.2f} kr/kWh."
        )

    return EnergyStrategySnapshot(
        site_slug=site_slug,
        period_start=period_start,
        market_price_sek_kwh=market,
        import_price_sek_kwh=import_price,
        export_price_sek_kwh=export_price,
        market_quality=current.quality if current else PriceQuality.MISSING,
        import_quality=current.quality if current else PriceQuality.MISSING,
        export_quality=current.quality if current else PriceQuality.MISSING,
        battery_soc_pct=battery_soc_pct,
        strategy_state=state,
        confidence=confidence,
        reason=reason,
        reason_sv=reason_sv,
        next_peak_at=peak[0] if peak else None,
        next_peak_import_sek_kwh=peak[1] if peak else None,
        optimization_mode=optimization_mode,
        expected_saving_today_sek=estimate_shiftable_savings(horizon, config=eov_config),
        recommended_reserve_soc_pct=reserve,
        recommended_action=recommended_action,
        eov_value_sek_kwh=eov_value,
        grid_surcharge_sek_kwh=tariff.grid_surcharge_sek_kwh if tariff else None,
        fuse_headroom_a=peak_hint.fuse_headroom_a if peak_hint else None,
        fuse_utilization_pct=peak_hint.utilization_pct if peak_hint else None,
        ev_recommendations=ev_snaps,
    )


def _find_import_peak(periods: tuple[PricePeriod, ...]) -> tuple[datetime, float] | None:
    best: tuple[datetime, float] | None = None
    window_end = datetime.now(UTC) + timedelta(hours=24)
    for period in periods:
        start = _as_utc(period.period_start)
        if start > window_end:
            break
        price = period.import_price_sek_kwh
        if price is None:
            continue
        if best is None or price > best[1]:
            best = (start, price)
    return best


def _heuristic_state(
    *,
    current_import: float | None,
    peak_import: float | None,
    export_price: float | None,
) -> tuple[StrategyState, float, str, str]:
    if current_import is None:
        return (
            StrategyState.NORMAL_SELF_USE,
            0.2,
            "Import price unavailable; using conservative self-use posture.",
            "Importpris saknas; EMIC använder konservativ egenförbrukning.",
        )

    if peak_import is not None and peak_import > current_import * 1.35:
        return (
            StrategyState.PEAK_AHEAD,
            0.55,
            (
                f"Higher import prices expected later (peak ~{peak_import:.2f} SEK/kWh). "
                "EOV unavailable — price heuristic only."
            ),
            (
                f"Högre importpris väntas senare (topp ~{peak_import:.2f} kr/kWh). "
                "EOV saknas — prisheuristik."
            ),
        )

    if export_price is not None and export_price > current_import * 0.9:
        return (
            StrategyState.NORMAL_SELF_USE,
            0.45,
            "Export compensation is relatively strong versus current import cost.",
            "Exportersättningen är relativt hög jämfört med nuvarande importpris.",
        )

    return (
        StrategyState.NORMAL_SELF_USE,
        0.4,
        "No strong price signal; normal self-use recommended.",
        "Ingen tydlig prissignal; normal egenförbrukning rekommenderas.",
    )


def _recommended_reserve(battery_soc_pct: float | None, peak_import: float | None) -> float | None:
    if battery_soc_pct is None:
        return None
    if peak_import is None:
        return max(25.0, battery_soc_pct - 15.0)
    if peak_import >= 2.5:
        return 58.0
    if peak_import >= 1.8:
        return 45.0
    return 30.0


def _format_local_hhmm(ts: datetime, timezone: str) -> str:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return ts.astimezone(ZoneInfo(timezone)).strftime("%H:%M")
