"""Build 15-minute Heartbeat audit period snapshots."""

from __future__ import annotations

from datetime import UTC, datetime

from energy_core.heartbeat_audit.types import AuditPeriodSnapshot
from energy_core.price_engine.strategy import build_strategy_snapshot
from energy_core.price_engine.types import OptimizationMode, PricePeriod


def _as_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


def _nearest_before(
    records: tuple[tuple[datetime, dict[str, float | None]], ...],
    target: datetime,
) -> dict[str, float | None] | None:
    target = _as_utc(target)
    best: dict[str, float | None] | None = None
    for ts, payload in records:
        if _as_utc(ts) <= target:
            best = payload
        else:
            break
    return best


def _nearest_decision(
    decisions: tuple[tuple[datetime, dict[str, str | None]], ...],
    target: datetime,
) -> dict[str, str | None] | None:
    target = _as_utc(target)
    best: dict[str, str | None] | None = None
    for ts, payload in decisions:
        if _as_utc(ts) <= target:
            best = payload
        else:
            break
    return best


def build_period_snapshots(
    *,
    site_slug: str,
    timezone: str,
    periods: tuple[PricePeriod, ...],
    readings: tuple[tuple[datetime, dict[str, float | None]], ...],
    decisions: tuple[tuple[datetime, dict[str, str | None]], ...],
    optimization_mode: OptimizationMode = OptimizationMode.MONITOR_ONLY,
    now: datetime | None = None,
    max_periods: int = 96,
) -> tuple[AuditPeriodSnapshot, ...]:
    """Merge price, telemetry, Heartbeat intent, and EMIC strategy per period."""
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    horizon = periods
    snapshots: list[AuditPeriodSnapshot] = []
    for period in periods[:max_periods]:
        if _as_utc(period.period_start) > now:
            break
        reading = _nearest_before(readings, period.period_start)
        decision = _nearest_decision(decisions, period.period_start)
        strategy = build_strategy_snapshot(
            site_slug=site_slug,
            timezone=timezone,
            current=period,
            horizon=horizon,
            battery_soc_pct=reading.get("battery_soc_pct") if reading else None,
            optimization_mode=optimization_mode,
            now=period.period_start,
        )
        snapshots.append(
            AuditPeriodSnapshot(
                period_start=period.period_start,
                period_end=period.period_end,
                import_price_sek_kwh=period.import_price_sek_kwh,
                export_price_sek_kwh=period.export_price_sek_kwh,
                grid_import_w=reading.get("grid_import_w") if reading else None,
                grid_export_w=reading.get("grid_export_w") if reading else None,
                battery_soc_pct=reading.get("battery_soc_pct") if reading else None,
                ev_power_w=reading.get("ev_power_w") if reading else None,
                heartbeat_mode=decision.get("heartbeat_mode") if decision else None,
                ai_decision=decision.get("ai_decision") if decision else None,
                heartbeat_reason=decision.get("reason") if decision else None,
                emic_strategy_state=strategy.strategy_state.value,
                emic_recommended_action=strategy.recommended_action,
            )
        )
    return tuple(snapshots)
