"""Arctic Spa fixed filter cycle policy — 4 × 2 h default hygiene requirement."""

from __future__ import annotations

import json
from dataclasses import dataclass

from energy_core.spa_energy.cleaning_schedule import CleaningConfigValidation, allowed_window_hours


@dataclass(frozen=True, slots=True)
class SpaFilterPolicy:
    """EMIC optimizes start times; Arctic Spa retains filter responsibility."""

    cycles_per_day: int = 4
    duration_per_cycle_minutes: int = 120
    minimum_cycle_separation_minutes: int = 60
    optimization_enabled: bool = True
    earliest_start: str = "07:00"
    latest_finish: str = "22:00"

    @property
    def total_daily_runtime_minutes(self) -> int:
        return self.cycles_per_day * self.duration_per_cycle_minutes

    @property
    def total_daily_runtime_hours(self) -> float:
        return self.total_daily_runtime_minutes / 60.0

    def validate(self) -> CleaningConfigValidation:
        if self.cycles_per_day < 1 or self.duration_per_cycle_minutes < 15:
            return CleaningConfigValidation(
                feasible=False,
                warning_sv="Filtercykler måste vara minst 15 minuter och minst en cykel per dygn.",
            )
        window_hours = allowed_window_hours(self.earliest_start, self.latest_finish)
        cycle_hours = self.duration_per_cycle_minutes / 60.0
        if cycle_hours > window_hours:
            return CleaningConfigValidation(
                feasible=False,
                warning_sv=(
                    f"Varje filtercykel ({self.duration_per_cycle_minutes} min) är längre än "
                    f"tidsfönstret {self.earliest_start}–{self.latest_finish}."
                ),
            )
        separation_hours = self.minimum_cycle_separation_minutes / 60.0
        min_span = (
            self.cycles_per_day * cycle_hours
            + max(0, self.cycles_per_day - 1) * separation_hours
        )
        if min_span > window_hours + 1e-9:
            return CleaningConfigValidation(
                feasible=False,
                warning_sv=(
                    f"{self.cycles_per_day} cykler à {self.duration_per_cycle_minutes} min "
                    f"med minst {self.minimum_cycle_separation_minutes} min paus kräver "
                    f"{min_span:g} h men fönstret är {window_hours:g} h."
                ),
                max_achievable_hours=window_hours,
            )
        return CleaningConfigValidation(
            feasible=True,
            max_achievable_hours=self.total_daily_runtime_hours,
        )

    def summary_sv(self) -> str:
        return (
            f"Arctic Spa grundschema: {self.cycles_per_day} cykler per dygn, "
            f"{self.duration_per_cycle_minutes // 60} h per cykel "
            f"({self.total_daily_runtime_hours:g} h totalt) mellan "
            f"{self.earliest_start} och {self.latest_finish}."
        )

    def optimization_summary_sv(self) -> str:
        if self.optimization_enabled:
            return (
                "EMIC ändrar när de fyra filtercyklerna körs men ändrar inte "
                "den totala filtreringstiden."
            )
        return "Smart filteroptimering är av — Arctic Spa kör sitt interna schema."

    @classmethod
    def from_control(cls, control) -> SpaFilterPolicy:
        cycles = getattr(control, "filter_cycles_per_day", None)
        if cycles is None:
            cycles = control.max_starts_per_day
        duration = getattr(control, "filter_duration_minutes", None)
        if duration is None:
            duration = control.min_run_minutes
        separation = getattr(control, "minimum_cycle_separation_minutes", None)
        if separation is None:
            separation = control.min_stop_minutes
        optimization = getattr(control, "filter_optimization_enabled", True)
        return cls(
            cycles_per_day=int(cycles),
            duration_per_cycle_minutes=int(duration),
            minimum_cycle_separation_minutes=int(separation),
            optimization_enabled=bool(optimization),
            earliest_start=control.allowed_window_start,
            latest_finish=control.allowed_window_end,
        )

    def to_safe_schedule_json(self) -> str:
        return json.dumps(
            {
                "frequency": self.cycles_per_day,
                "duration_hours": max(1, self.duration_per_cycle_minutes // 60),
            }
        )

    @classmethod
    def safe_schedule_from_json(cls, raw: str | None) -> dict[str, int] | None:
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None
        freq = data.get("frequency")
        dur = data.get("duration_hours")
        if freq is None or dur is None:
            return None
        return {"frequency": max(1, int(freq)), "duration_hours": max(1, int(dur))}

    def sync_legacy_control_fields(self) -> dict[str, object]:
        """Keep legacy DB fields aligned with fixed filter policy."""
        return {
            "min_cleaning_hours_per_day": self.total_daily_runtime_hours,
            "max_starts_per_day": self.cycles_per_day,
            "min_run_minutes": self.duration_per_cycle_minutes,
            "min_stop_minutes": self.minimum_cycle_separation_minutes,
            "safety_floor_frequency_per_day": float(self.cycles_per_day),
            "safety_floor_duration_hours": max(1.0, self.duration_per_cycle_minutes / 60.0),
        }


def is_spa_filter_self_managed(control) -> bool:
    """True when Eco Pak owns filter timing — EMIC must not actuate cleaning."""
    if not getattr(control, "filter_optimization_enabled", True):
        return True
    if (
        getattr(control, "strategy", None) == "FIXED_SCHEDULE"
        and getattr(control, "fixed_schedule_start", None)
        and getattr(control, "fixed_schedule_end", None)
    ):
        return True
    return False
