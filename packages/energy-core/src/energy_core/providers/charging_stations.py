"""Charging station provider wiring."""

from __future__ import annotations

from energy_core.integrations.charging_stations.abstractions import IChargingStationProvider
from energy_core.integrations.charging_stations.chargefinder.provider import ChargeFinderChargingStationProvider
from energy_core.integrations.charging_stations.chargefinder_metrics import get_chargefinder_metrics
from energy_core.integrations.charging_stations.models import (
    ChargingStationCandidate,
    ResolvedChargingLocation,
    StationCandidateScore,
    StationResolutionStatus,
)

__all__ = [
    "ChargeFinderChargingStationProvider",
    "ChargingStationCandidate",
    "IChargingStationProvider",
    "ResolvedChargingLocation",
    "StationCandidateScore",
    "StationResolutionStatus",
    "get_chargefinder_metrics",
]
