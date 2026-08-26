"""Ridge calibration for interpretable learned correction."""

from __future__ import annotations

import hashlib
import json
import logging
import math
from datetime import UTC, date, datetime

from energy_core.config import Settings, get_settings
from energy_core.solar_intelligence.types import INTELLIGENCE_MODEL_VERSION, SolarModelRecord, TrainingSample

logger = logging.getLogger(__name__)

try:
    from sklearn.linear_model import Ridge
except ImportError:  # pragma: no cover - optional at import
    Ridge = None  # type: ignore[misc, assignment]


FEATURE_NAMES = (
    "hour_sin",
    "hour_cos",
    "doy_sin",
    "doy_cos",
    "solar_elevation",
    "poa_irradiance",
    "ghi",
    "cloud_cover",
    "temperature",
    "installed_kwp",
    "panel_tilt",
    "panel_azimuth",
)


def _cyclical(value: float, period: float) -> tuple[float, float]:
    angle = 2.0 * math.pi * value / period
    return math.sin(angle), math.cos(angle)


def build_feature_vector(sample: TrainingSample, *, installed_kwp: float, tilt: float, azimuth: float) -> list[float]:
    hour = float(sample.hour_utc)
    doy = float(sample.sample_date.timetuple().tm_yday)
    h_sin, h_cos = _cyclical(hour, 24.0)
    d_sin, d_cos = _cyclical(doy, 365.0)
    return [
        h_sin,
        h_cos,
        d_sin,
        d_cos,
        sample.solar_elevation_deg or 0.0,
        sample.poa_wm2 or 0.0,
        sample.ghi_wm2 or 0.0,
        sample.cloud_cover_pct or 0.0,
        sample.temperature_c or 0.0,
        installed_kwp,
        tilt,
        azimuth,
    ]


def _metrics(actuals: list[float], predicted: list[float]) -> dict[str, float | None]:
    if not actuals:
        return {"mae": None, "mape": None, "wape": None, "rmse": None, "r2": None, "bias_pct": None}
    n = len(actuals)
    errors = [abs(a - p) for a, p in zip(actuals, predicted, strict=True)]
    signed = [p - a for a, p in zip(actuals, predicted, strict=True)]
    sq = [e * e for e in signed]
    sum_actual = sum(actuals)
    mae = sum(errors) / n
    rmse = math.sqrt(sum(sq) / n)
    wape = sum(errors) / sum_actual * 100.0 if sum_actual > 0 else None
    mape_vals = [abs(a - p) / a * 100.0 for a, p in zip(actuals, predicted, strict=True) if a >= 1.0]
    mape = sum(mape_vals) / len(mape_vals) if mape_vals else None
    mean_a = sum_actual / n
    ss_res = sum((a - p) ** 2 for a, p in zip(actuals, predicted, strict=True))
    ss_tot = sum((a - mean_a) ** 2 for a in actuals)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else None
    bias = sum(signed) / sum_actual * 100.0 if sum_actual > 0 else None
    return {
        "mae": round(mae, 4),
        "mape": round(mape, 2) if mape is not None else None,
        "wape": round(wape, 2) if wape is not None else None,
        "rmse": round(rmse, 4),
        "r2": round(r2, 4) if r2 is not None else None,
        "bias_pct": round(bias, 2) if bias is not None else None,
    }


class SolarCalibrationService:
    """Train Ridge model: correction_pct = f(features); final = physical * (1 + correction)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def train(
        self,
        site_id: int,
        samples: list[TrainingSample],
        *,
        installed_kwp: float,
        tilt: float,
        azimuth: float,
        training_from: date | None = None,
        training_to: date | None = None,
        holdout_days: int = 14,
    ) -> SolarModelRecord | None:
        if Ridge is None:
            logger.error("scikit-learn not installed; cannot train solar model")
            return None

        eligible = [
            s
            for s in samples
            if s.physical_kwh and s.physical_kwh > 0 and s.actual_kwh is not None and s.actual_kwh >= 0
        ]
        min_samples = self._settings.solar_forecast_min_samples_preliminary
        if len(eligible) < min_samples:
            logger.info("Insufficient training samples site=%s count=%d need=%d", site_id, len(eligible), min_samples)
            return None

        holdout_cutoff = (training_to or date.today()).toordinal() - holdout_days
        train_set = [s for s in eligible if s.sample_date.toordinal() < holdout_cutoff]
        holdout = [s for s in eligible if s.sample_date.toordinal() >= holdout_cutoff]
        if len(train_set) < min_samples:
            train_set = eligible
            holdout = []

        x_train = [build_feature_vector(s, installed_kwp=installed_kwp, tilt=tilt, azimuth=azimuth) for s in train_set]
        y_train = [
            (s.actual_kwh - s.physical_kwh) / s.physical_kwh if s.physical_kwh else 0.0  # type: ignore[operator]
            for s in train_set
        ]

        model = Ridge(alpha=1.0)
        model.fit(x_train, y_train)

        coef_map = {name: float(c) for name, c in zip(FEATURE_NAMES, model.coef_, strict=True)}
        coef_map["intercept"] = float(model.intercept_)

        eval_samples = holdout or train_set[-min(14, len(train_set)) :]
        actuals: list[float] = []
        predicted: list[float] = []
        for s in eval_samples:
            x = build_feature_vector(s, installed_kwp=installed_kwp, tilt=tilt, azimuth=azimuth)
            corr = float(model.predict([x])[0])
            corr = max(-0.5, min(0.5, corr))
            pred = s.physical_kwh * (1.0 + corr)  # type: ignore[operator]
            actuals.append(s.actual_kwh)  # type: ignore[arg-type]
            predicted.append(pred)

        metrics = _metrics(actuals, predicted)
        config_hash = hashlib.sha256(
            json.dumps({"kwp": installed_kwp, "tilt": tilt, "azimuth": azimuth}, sort_keys=True).encode()
        ).hexdigest()[:16]

        return SolarModelRecord(
            site_id=site_id,
            role="challenger",
            model_version=INTELLIGENCE_MODEL_VERSION,
            trained_at=datetime.now(UTC),
            sample_count=len(eligible),
            mae=metrics["mae"],
            mape=metrics["mape"],
            wape=metrics["wape"],
            rmse=metrics["rmse"],
            r2=metrics["r2"],
            bias_pct=metrics["bias_pct"],
            features={name: 1.0 for name in FEATURE_NAMES},
            coefficients=coef_map,
        )


def should_promote_challenger(champion: SolarModelRecord | None, challenger: SolarModelRecord) -> bool:
    if champion is None:
        return True
    if challenger.wape is None:
        return False
    if champion.wape is None:
        return True
    return challenger.wape < champion.wape
