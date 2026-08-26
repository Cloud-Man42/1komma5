"""Shadow mode comparison: actual vs EMIC-optimized schedule."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ShadowComparisonDay:
    date_label: str
    actual_cost_sek: float
    optimized_cost_sek: float
    potential_saving_sek: float
    actual_energy_kwh: float
    optimized_energy_kwh: float


@dataclass(frozen=True, slots=True)
class ShadowComparisonResult:
    days: tuple[ShadowComparisonDay, ...]
    total_actual_cost_sek: float
    total_optimized_cost_sek: float
    total_potential_saving_sek: float
    shadow_mode_active: bool
    period_start: datetime
    period_end: datetime


class SpaShadowModeAnalyzer:
    """Compare actual spa intervals against what EMIC would have planned."""

    def compare(
        self,
        *,
        actual_by_day: dict[str, tuple[float, float]],
        optimized_by_day: dict[str, tuple[float, float]],
        shadow_mode_active: bool,
        period_start: datetime,
        period_end: datetime,
    ) -> ShadowComparisonResult:
        days: list[ShadowComparisonDay] = []
        total_actual = 0.0
        total_optimized = 0.0

        all_keys = sorted(set(actual_by_day) | set(optimized_by_day))
        for key in all_keys:
            actual_energy, actual_cost = actual_by_day.get(key, (0.0, 0.0))
            opt_energy, opt_cost = optimized_by_day.get(key, (0.0, 0.0))
            saving = max(0.0, actual_cost - opt_cost)
            days.append(
                ShadowComparisonDay(
                    date_label=key,
                    actual_cost_sek=actual_cost,
                    optimized_cost_sek=opt_cost,
                    potential_saving_sek=saving,
                    actual_energy_kwh=actual_energy,
                    optimized_energy_kwh=opt_energy,
                )
            )
            total_actual += actual_cost
            total_optimized += opt_cost

        return ShadowComparisonResult(
            days=tuple(days),
            total_actual_cost_sek=total_actual,
            total_optimized_cost_sek=total_optimized,
            total_potential_saving_sek=max(0.0, total_actual - total_optimized),
            shadow_mode_active=shadow_mode_active,
            period_start=period_start,
            period_end=period_end,
        )
