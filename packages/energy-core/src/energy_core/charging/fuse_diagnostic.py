"""Read-only fuse headroom diagnostics — not used for charging control."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from energy_core.charging.config import ChargingConfig
from energy_core.charging.power_to_current import power_to_current_a
from energy_core.energy.state import EnergyState

if TYPE_CHECKING:
    from energy_core.db.models import EvChargerModel, SiteModel


@dataclass(frozen=True, slots=True)
class FuseDiagnostic:
    headroom_a: float | None
    limiting_phase_a: float | None
    grid_import_headroom_w: float | None


def compute_fuse_diagnostic(state: EnergyState, config: ChargingConfig) -> FuseDiagnostic:
    """Compute conservative fuse headroom for diagnostics and readiness only."""
    headroom_values: list[float] = []
    limiting_phase: float | None = None
    if config.main_fuse_a is not None:
        fuse_headroom = max(0.0, config.main_fuse_a - config.safety_margin_a)
        phase_values = [state.phase_current_l1_a, state.phase_current_l2_a, state.phase_current_l3_a]
        if any(value is not None for value in phase_values):
            for phase_current in phase_values:
                if phase_current is None:
                    continue
                available = max(0.0, fuse_headroom - phase_current)
                headroom_values.append(available)
                if limiting_phase is None or available < limiting_phase:
                    limiting_phase = available
        else:
            headroom_values.append(fuse_headroom)
            limiting_phase = fuse_headroom

    grid_import_headroom_w: float | None = None
    if config.max_grid_import_w is not None and state.grid_import_w is not None:
        grid_import_headroom_w = max(0.0, config.max_grid_import_w - state.grid_import_w)
        headroom_values.append(
            power_to_current_a(
                grid_import_headroom_w,
                phases=config.phases,
                nominal_voltage_v=config.nominal_voltage_v,
                min_current_a=0.0,
                max_current_a=config.max_current_a,
                max_power_w=config.max_power_w,
            )
        )

    if not headroom_values:
        return FuseDiagnostic(headroom_a=None, limiting_phase_a=None, grid_import_headroom_w=grid_import_headroom_w)
    return FuseDiagnostic(
        headroom_a=min(headroom_values),
        limiting_phase_a=limiting_phase,
        grid_import_headroom_w=grid_import_headroom_w,
    )


def fuse_headroom_a_for_charger(
    charger: EvChargerModel,
    site: SiteModel,
    *,
    energy: EnergyState | None = None,
    phase_current_l1_a: float | None = None,
    phase_current_l2_a: float | None = None,
    phase_current_l3_a: float | None = None,
) -> float | None:
    """Read-only fuse headroom for bridge-status diagnostics."""
    if energy is None:
        resolved = EnergyState(
            timestamp=datetime.now(UTC),
            phase_current_l1_a=phase_current_l1_a,
            phase_current_l2_a=phase_current_l2_a,
            phase_current_l3_a=phase_current_l3_a,
        )
    else:
        resolved = energy
    config = ChargingConfig(
        max_current_a=charger.max_current_a or 16.0,
        min_current_a=charger.min_current_a or 6.0,
        phases=charger.phases or 3,
        nominal_voltage_v=charger.nominal_voltage_v or 230.0,
        max_power_w=charger.max_power_w,
        max_grid_import_w=charger.max_grid_import_w,
        main_fuse_a=site.main_fuse_a,
        safety_margin_a=site.safety_margin_a or 2.0,
        solar_start_threshold_w=charger.solar_start_threshold_w or 1500.0,
        solar_stop_threshold_w=charger.solar_stop_threshold_w or 800.0,
        solar_start_delay_seconds=float(charger.solar_start_delay_seconds or 30),
        solar_stop_delay_seconds=float(charger.solar_stop_delay_seconds or 60),
        timezone=site.timezone or "Europe/Stockholm",
    )
    return compute_fuse_diagnostic(resolved, config).headroom_a
