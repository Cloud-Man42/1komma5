"""Solar forecast tuning constants."""

from __future__ import annotations

# Correction bounds
MIN_CORRECTION_FACTOR = 0.5
MAX_CORRECTION_FACTOR = 1.5
MIN_SAMPLES_FOR_CORRECTION = 5
SHRINKAGE_STRENGTH = 20.0

# Recency weights (days -> weight multiplier)
RECENCY_WEIGHTS: tuple[tuple[int, float], ...] = (
    (7, 1.0),
    (30, 0.6),
    (365, 0.3),
)

# Confidence quality thresholds
CONFIDENCE_HIGH = 0.80
CONFIDENCE_MEDIUM = 0.60

# Smart charging planning factors by quality
PLANNING_FACTORS: dict[str, float] = {
    "HIGH": 0.95,
    "MEDIUM": 0.80,
    "LOW": 0.60,
    "INSUFFICIENT_DATA": 0.0,
}

# Physical model
TEMP_COEFFICIENT_PER_C = -0.004  # power loss per °C above 25°C
REFERENCE_TEMP_C = 25.0
DEFAULT_TILT_DEG = 35.0
DEFAULT_AZIMUTH_DEG = 180.0  # south in EMIC convention

# Anomaly detection
ANOMALY_BASELINE_MIN_KWH = 0.05
ANOMALY_RATIO_THRESHOLD = 0.15  # actual/baseline below this with high baseline
MIN_COVERAGE_FRACTION = 0.5

# Interval energy from average power
INTERVAL_HOURS = 15 / 60.0


def diurnal_solar_factor(hour: float) -> float:
    """Gaussian-ish solar elevation proxy for local hour of day (0–23)."""
    import math

    if hour < 6 or hour > 20:
        return 0.0
    x = (hour - 13) / 4.0
    return math.exp(-0.5 * x * x)
