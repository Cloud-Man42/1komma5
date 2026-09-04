"""Heartbeat optimization efficiency metrics."""


def compute_heartbeat_efficiency_pct(
    *,
    heartbeat_saving_sek: float,
    baseline_cost_sek: float,
    emic_theoretical_optimal_cost_sek: float,
) -> float | None:
    """Return Heartbeat efficiency percentage per Phase 4 spec."""
    denominator = baseline_cost_sek - emic_theoretical_optimal_cost_sek + heartbeat_saving_sek
    if denominator <= 0:
        return None
    if heartbeat_saving_sek <= 0:
        return 0.0
    return round(min(100.0, (heartbeat_saving_sek / denominator) * 100.0), 1)
