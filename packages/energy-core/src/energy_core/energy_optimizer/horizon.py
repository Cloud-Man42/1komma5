"""Read-only Horizon Optimizer (Phase 14)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from energy_core.flexible_load.orchestrator import OrchestratedLoadPlan, OrchestratedLoadSpec
from energy_core.flexible_load.types import HorizonBlock


def load_type_from_id(load_id: str) -> str:
    if load_id == "spa_cleaning":
        return "spa"
    if load_id.startswith("ev_charger_"):
        return "ev"
    return "other"


@dataclass(frozen=True, slots=True)
class HorizonLoadRecommendation:
    load_id: str
    name: str
    load_type: str
    priority: int
    strategy: str
    window_start: datetime | None = None
    window_end: datetime | None = None
    expected_energy_kwh: float | None = None
    expected_cost_sek: float | None = None
    expected_energy_source: str | None = None
    savings_sek: float | None = None
    reason_sv: str | None = None
    explanation_sv: str | None = None


@dataclass(frozen=True, slots=True)
class HorizonOptimizerSnapshot:
    available: bool
    monitor_only: bool
    unavailable_reason_sv: str | None = None
    horizon_hours: int = 48
    horizon_blocks: int = 0
    generated_at: datetime | None = None
    total_planned_savings_sek: float | None = None
    headline_sv: str | None = None
    summary_sv: str | None = None
    loads: tuple[HorizonLoadRecommendation, ...] = ()


def _recommendation_from_result(result: OrchestratedLoadPlan) -> HorizonLoadRecommendation:
    window = result.plan.windows[0] if result.plan.windows else None
    return HorizonLoadRecommendation(
        load_id=result.load_id,
        name=result.name,
        load_type=load_type_from_id(result.load_id),
        priority=result.priority,
        strategy=result.plan.strategy.value,
        window_start=window.start if window else None,
        window_end=window.end if window else None,
        expected_energy_kwh=window.expected_energy_kwh if window else None,
        expected_cost_sek=window.expected_cost_sek if window else None,
        expected_energy_source=window.expected_energy_source.value if window else None,
        savings_sek=result.plan.savings_sek,
        reason_sv=result.plan.reason_sv,
        explanation_sv=result.plan.explanation_sv,
    )


def build_horizon_optimizer_snapshot(
    *,
    specs: tuple[OrchestratedLoadSpec, ...],
    horizon: tuple[HorizonBlock, ...],
    results: tuple[OrchestratedLoadPlan, ...],
    now: datetime,
    horizon_hours: int = 48,
) -> HorizonOptimizerSnapshot:
    if not specs:
        return HorizonOptimizerSnapshot(
            available=False,
            monitor_only=True,
            unavailable_reason_sv="Inga flexibla laster är konfigurerade på siten.",
            generated_at=now,
        )

    if not horizon:
        return HorizonOptimizerSnapshot(
            available=False,
            monitor_only=True,
            unavailable_reason_sv="Prognosdata saknas — horizon-plan kan inte beräknas.",
            generated_at=now,
            horizon_hours=horizon_hours,
        )

    loads = tuple(_recommendation_from_result(result) for result in results)
    savings = [load.savings_sek for load in loads if load.savings_sek is not None]
    total_savings = round(sum(savings), 2) if savings else None
    planned = sum(1 for load in loads if load.window_start is not None)
    missing = len(loads) - planned

    if planned == 0:
        headline = "Ingen lämplig körplan hittades i horisonten"
        summary = "Kontrollera deadlines, prioriteter och prognoskvalitet."
    elif missing == 0:
        headline = f"Koordinerad {horizon_hours}h-plan för {len(loads)} laster"
        summary = (
            f"Beräknad besparing: {total_savings:.2f} kr."
            if total_savings is not None
            else "Alla laster har planerade fönster."
        )
    else:
        headline = f"Delvis horizon-plan — {missing} laster saknar fönster"
        summary = (
            f"{planned} av {len(loads)} laster planerade"
            + (f"; uppskattad besparing {total_savings:.2f} kr." if total_savings is not None else ".")
        )

    return HorizonOptimizerSnapshot(
        available=True,
        monitor_only=True,
        horizon_hours=horizon_hours,
        horizon_blocks=len(horizon),
        generated_at=now,
        total_planned_savings_sek=total_savings,
        headline_sv=headline,
        summary_sv=summary,
        loads=loads,
    )
