"""Energy source attribution for EV charging intervals."""

from __future__ import annotations

from energy_core.ev_accounting.constants import ATTRIBUTION_TOLERANCE_FRACTION, ATTRIBUTION_TOLERANCE_KWH
from energy_core.ev_accounting.models import (
    AttributionResult,
    BatteryDischargeSplit,
    EnergyAttribution,
    SiteEnergySample,
)


class EnergyAttributionEngine:
    """Attribute EV charged energy to four source categories."""

    def attribute_interval(
        self,
        charged_kwh: float,
        sample: SiteEnergySample,
        *,
        battery_discharge: BatteryDischargeSplit | None = None,
        ev_power_w: float | None = None,
    ) -> AttributionResult:
        if charged_kwh <= 0:
            return AttributionResult(
                attribution=EnergyAttribution(),
                confidence=1.0,
                data_quality="MEASURED",
            )

        ev_kwh = charged_kwh
        confidence = 0.8
        quality = "CALCULATED"

        # 1. Solar direct — conservative available solar for EV
        non_ev_house_kwh = max(0.0, sample.house_kwh - ev_kwh)
        pv_surplus = max(0.0, sample.pv_kwh - non_ev_house_kwh - sample.battery_charge_kwh)
        if sample.grid_export_kwh > 0 and ev_kwh > 0:
            pv_surplus = max(pv_surplus, min(sample.grid_export_kwh, ev_kwh))
        solar_direct = min(ev_kwh, pv_surplus)
        remaining = ev_kwh - solar_direct

        # 2. Battery discharge to EV
        solar_battery = 0.0
        grid_battery = 0.0
        if battery_discharge is not None and remaining > 0 and sample.battery_discharge_kwh > 0:
            discharge_to_ev = min(remaining, battery_discharge.solar_kwh + battery_discharge.grid_kwh)
            if battery_discharge.solar_kwh + battery_discharge.grid_kwh > 0:
                total_discharge = battery_discharge.solar_kwh + battery_discharge.grid_kwh
                solar_battery = discharge_to_ev * (battery_discharge.solar_kwh / total_discharge)
                grid_battery = discharge_to_ev * (battery_discharge.grid_kwh / total_discharge)
            remaining -= discharge_to_ev

        # 3. Grid direct — attributable import after other loads
        grid_direct = 0.0
        if remaining > 0 and sample.grid_import_kwh > 0:
            # Not all import goes to EV; cap by remaining EV energy and import
            non_ev_import = max(0.0, sample.grid_import_kwh - remaining)
            attributable_import = max(0.0, sample.grid_import_kwh - non_ev_import)
            grid_direct = min(remaining, attributable_import)
            remaining -= grid_direct

        # 4. Fill remainder deterministically as grid direct (conservative)
        if remaining > 0:
            grid_direct += remaining
            remaining = 0.0

        attribution = EnergyAttribution(
            solar_direct_kwh=round(solar_direct, 4),
            solar_battery_kwh=round(solar_battery, 4),
            grid_battery_kwh=round(grid_battery, 4),
            grid_direct_kwh=round(grid_direct, 4),
        )

        if ev_power_w is not None and ev_power_w <= 0 and charged_kwh > 0:
            confidence = 0.5
            quality = "ESTIMATED"

        if not _within_tolerance(attribution.total_kwh, ev_kwh):
            attribution = _scale_attribution(attribution, ev_kwh)
            confidence = min(confidence, 0.7)

        return AttributionResult(attribution=attribution, confidence=confidence, data_quality=quality)


def _within_tolerance(attributed: float, target: float) -> bool:
    if target <= 0:
        return attributed <= ATTRIBUTION_TOLERANCE_KWH
    delta = abs(attributed - target)
    return delta <= ATTRIBUTION_TOLERANCE_KWH or delta / target <= ATTRIBUTION_TOLERANCE_FRACTION


def _scale_attribution(attribution: EnergyAttribution, target: float) -> EnergyAttribution:
    total = attribution.total_kwh
    if total <= 0:
        return EnergyAttribution(grid_direct_kwh=target)
    factor = target / total
    return EnergyAttribution(
        solar_direct_kwh=round(attribution.solar_direct_kwh * factor, 4),
        solar_battery_kwh=round(attribution.solar_battery_kwh * factor, 4),
        grid_battery_kwh=round(attribution.grid_battery_kwh * factor, 4),
        grid_direct_kwh=round(attribution.grid_direct_kwh * factor, 4),
    )
