"""Peak / fuse headroom hints for energy strategy (display only)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PeakProtectionHint:
    fuse_headroom_a: float | None
    grid_import_w: float | None
    main_fuse_a: float
    utilization_pct: float
    reason: str
    reason_sv: str


def assess_peak_protection(
    *,
    main_fuse_a: float | None,
    safety_margin_a: float = 2.0,
    grid_import_w: float | None,
    phases: int = 3,
    nominal_voltage_v: float = 230.0,
    headroom_threshold_a: float = 4.0,
    utilization_threshold_pct: float = 85.0,
) -> PeakProtectionHint | None:
    """Return a peak-protection hint when the site fuse is near capacity."""
    if main_fuse_a is None or main_fuse_a <= 0:
        return None

    fuse_headroom_a: float | None = None
    utilization_pct = 0.0

    if grid_import_w is not None and grid_import_w > 0:
        estimated_phase_a = grid_import_w / max(phases * nominal_voltage_v, 1.0)
        available = max(0.0, main_fuse_a - safety_margin_a)
        fuse_headroom_a = max(0.0, available - estimated_phase_a)
        utilization_pct = min(100.0, (estimated_phase_a / max(main_fuse_a, 0.1)) * 100.0)
    else:
        return None

    if fuse_headroom_a > headroom_threshold_a and utilization_pct < utilization_threshold_pct:
        return None

    return PeakProtectionHint(
        fuse_headroom_a=round(fuse_headroom_a, 1),
        grid_import_w=round(grid_import_w, 0),
        main_fuse_a=main_fuse_a,
        utilization_pct=round(utilization_pct, 1),
        reason=(
            f"Main fuse ({main_fuse_a:.0f} A) utilization ~{utilization_pct:.0f}% — "
            f"limited headroom ({fuse_headroom_a:.1f} A). Avoid new large loads."
        ),
        reason_sv=(
            f"Huvudsäkring ({main_fuse_a:.0f} A) utnyttjad ~{utilization_pct:.0f}% — "
            f"begränsat utrymme ({fuse_headroom_a:.1f} A). Undvik nya stora laster."
        ),
    )
