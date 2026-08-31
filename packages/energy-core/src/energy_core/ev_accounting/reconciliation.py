"""Reconcile interval sums with Charge Amps meter total."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from energy_core.ev_accounting.attribution import _scale_attribution
from energy_core.ev_accounting.constants import ATTRIBUTION_TOLERANCE_KWH
from energy_core.ev_accounting.models import EnergyAttribution

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    attribution: EnergyAttribution
    measured_kwh: float | None
    attributed_kwh: float
    delta_kwh: float
    note: str
    energy_quality: str


class SessionReconciliationService:
    """Scale attributed energy to match measured session total when meter is authoritative."""

    def reconcile(
        self,
        attribution: EnergyAttribution,
        *,
        measured_kwh: float | None,
        attributed_kwh: float,
    ) -> ReconciliationResult:
        if measured_kwh is None:
            return ReconciliationResult(
                attribution=attribution,
                measured_kwh=None,
                attributed_kwh=attributed_kwh,
                delta_kwh=0.0,
                note="no_meter_reading",
                energy_quality="ESTIMATED",
            )

        delta = measured_kwh - attributed_kwh

        # A Charge Amps connector's consumption register resets when the car
        # unplugs, so stop-minus-start can read 0 for a session whose per-minute
        # meter deltas measured tens of kWh. Scaling to that zero used to wipe
        # the whole attribution — energy and source split — while the interval
        # costs survived, leaving sessions showing 0 kWh for 151 kr. The meter
        # only wins when it does not contradict positive measured intervals.
        if measured_kwh <= 0 and attributed_kwh > ATTRIBUTION_TOLERANCE_KWH:
            return ReconciliationResult(
                attribution=attribution,
                measured_kwh=measured_kwh,
                attributed_kwh=attributed_kwh,
                delta_kwh=delta,
                note="meter_register_reset",
                energy_quality="ESTIMATED",
            )

        if abs(delta) <= ATTRIBUTION_TOLERANCE_KWH:
            return ReconciliationResult(
                attribution=attribution,
                measured_kwh=measured_kwh,
                attributed_kwh=attributed_kwh,
                delta_kwh=delta,
                note="within_tolerance",
                energy_quality="MEASURED",
            )

        scaled = (
            _scale_attribution(attribution, measured_kwh)
            if attributed_kwh > 0
            else EnergyAttribution(grid_direct_kwh=measured_kwh)
        )
        logger.info(
            "session reconciliation measured=%.3f attributed=%.3f delta=%.3f",
            measured_kwh,
            attributed_kwh,
            delta,
        )
        return ReconciliationResult(
            attribution=scaled,
            measured_kwh=measured_kwh,
            attributed_kwh=attributed_kwh,
            delta_kwh=delta,
            note="scaled_to_meter",
            energy_quality="MEASURED",
        )
