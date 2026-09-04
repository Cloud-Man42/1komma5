"""Daily and monthly Heartbeat audit rollups."""

from __future__ import annotations

from energy_core.db.repositories import FinancialStat
from energy_core.energy_optimizer.eov import estimate_shiftable_savings
from energy_core.energy_optimizer.types import EovConfig
from energy_core.heartbeat_audit.efficiency import compute_heartbeat_efficiency_pct
from energy_core.heartbeat_audit.types import DailyAuditRollup, MonthlyAuditRollup
from energy_core.price_engine.types import PricePeriod


def _avg_prices(periods: tuple[PricePeriod, ...]) -> tuple[float | None, float | None]:
    imports = [p.import_price_sek_kwh for p in periods if p.import_price_sek_kwh is not None]
    exports = [p.export_price_sek_kwh for p in periods if p.export_price_sek_kwh is not None]
    avg_import = sum(imports) / len(imports) if imports else None
    avg_export = sum(exports) / len(exports) if exports else None
    return avg_import, avg_export


def build_daily_rollup(
    *,
    day: str,
    financial: FinancialStat,
    horizon: tuple[PricePeriod, ...],
    ev_savings_sek: float = 0.0,
    eov_config: EovConfig | None = None,
) -> DailyAuditRollup:
    actual = round(financial.grid_import_cost_sek - financial.export_revenue_sek, 2)
    consumed = (
        financial.solar_self_consumed_kwh
        + financial.battery_self_consumed_kwh
        + financial.imported_kwh
    )
    avg_import, avg_export = _avg_prices(horizon)

    if avg_import is not None and avg_export is not None:
        baseline = round(consumed * avg_import - financial.exported_kwh * avg_export, 2)
    else:
        baseline = actual

    heartbeat_saving = round(
        max(0.0, financial.solar_savings_sek + financial.battery_savings_sek + ev_savings_sek),
        2,
    )
    if heartbeat_saving <= 0 and baseline > actual:
        heartbeat_saving = round(baseline - actual, 2)

    emic_extra = estimate_shiftable_savings(horizon, config=eov_config) or 0.0
    emic_optimal = round(max(0.0, actual - emic_extra), 2)
    additional = round(max(0.0, actual - emic_optimal), 2)
    efficiency = compute_heartbeat_efficiency_pct(
        heartbeat_saving_sek=heartbeat_saving,
        baseline_cost_sek=baseline,
        emic_theoretical_optimal_cost_sek=emic_optimal,
    )

    return DailyAuditRollup(
        day=day,
        actual_energy_cost_sek=actual,
        baseline_cost_without_optimization_sek=baseline,
        heartbeat_saving_sek=heartbeat_saving,
        emic_theoretical_optimal_cost_sek=emic_optimal,
        additional_optimization_potential_sek=additional,
        heartbeat_efficiency_pct=efficiency,
        imported_kwh=financial.imported_kwh,
        exported_kwh=financial.exported_kwh,
        solar_self_consumed_kwh=financial.solar_self_consumed_kwh,
        battery_self_consumed_kwh=financial.battery_self_consumed_kwh,
        period_count=len(horizon),
    )


def aggregate_monthly_rollups(daily: tuple[DailyAuditRollup, ...]) -> MonthlyAuditRollup | None:
    if not daily:
        return None
    month = daily[0].day[:7]
    actual = round(sum(d.actual_energy_cost_sek for d in daily), 2)
    baseline = round(sum(d.baseline_cost_without_optimization_sek for d in daily), 2)
    heartbeat_saving = round(sum(d.heartbeat_saving_sek for d in daily), 2)
    emic_optimal = round(sum(d.emic_theoretical_optimal_cost_sek for d in daily), 2)
    additional = round(sum(d.additional_optimization_potential_sek for d in daily), 2)
    efficiency = compute_heartbeat_efficiency_pct(
        heartbeat_saving_sek=heartbeat_saving,
        baseline_cost_sek=baseline,
        emic_theoretical_optimal_cost_sek=emic_optimal,
    )
    return MonthlyAuditRollup(
        month=month,
        actual_energy_cost_sek=actual,
        baseline_cost_without_optimization_sek=baseline,
        heartbeat_saving_sek=heartbeat_saving,
        emic_theoretical_optimal_cost_sek=emic_optimal,
        additional_optimization_potential_sek=additional,
        heartbeat_efficiency_pct=efficiency,
        imported_kwh=round(sum(d.imported_kwh for d in daily), 3),
        exported_kwh=round(sum(d.exported_kwh for d in daily), 3),
        days_with_data=len(daily),
    )
