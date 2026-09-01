"""Shared charging station resolution models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class StationProvider(StrEnum):
    CHARGEFINDER = "CHARGEFINDER"
    LOCAL = "LOCAL"
    DIRECT_CHARGER = "DIRECT_CHARGER"
    MANUAL = "MANUAL"


class StationResolutionStatus(StrEnum):
    OK = "OK"
    DEGRADED = "DEGRADED"
    MULTIPLE_CANDIDATES = "MULTIPLE_CANDIDATES"
    UNKNOWN = "UNKNOWN"


class DataQuality(StrEnum):
    LIVE = "LIVE"
    CACHED = "CACHED"
    DEGRADED = "DEGRADED"


@dataclass(frozen=True, slots=True)
class ChargingStationCandidate:
    provider: StationProvider
    provider_station_id: str
    operator: str | None
    station_name: str | None
    latitude: float
    longitude: float
    network_name: str | None = None
    address: str | None = None
    postal_code: str | None = None
    city: str | None = None
    country: str | None = None
    connector_type: str | None = None
    max_power_kw: float | None = None
    charging_type: str | None = None
    distance_m: float | None = None
    price_model: str = "UNKNOWN"
    price_value_sek_kwh: float | None = None
    external_url: str | None = None
    realtime_status: str | None = None
    data_quality: DataQuality = DataQuality.LIVE
    raw_provider_data: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class StationCandidateScore:
    candidate: ChargingStationCandidate
    score: int
    label: str


@dataclass(frozen=True, slots=True)
class ResolvedChargingLocation:
    location_name: str
    station_name: str | None
    operator_name: str | None
    charging_type: str | None
    connector_type: str | None
    max_power_kw: float | None
    distance_meters: float | None
    confidence: int
    confidence_band: str
    identification_method: str
    source: str
    station_resolution_status: StationResolutionStatus
    candidates: list[StationCandidateScore] = field(default_factory=list)
    selected_station: ChargingStationCandidate | None = None
    charging_station_id: int | None = None
    price_model: str = "UNKNOWN"
    price_value_sek_kwh: float | None = None

    def to_cache_dict(self) -> dict:
        return {
            "location_name": self.location_name,
            "station_name": self.station_name,
            "operator_name": self.operator_name,
            "charging_type": self.charging_type,
            "connector_type": self.connector_type,
            "max_power_kw": self.max_power_kw,
            "distance_meters": self.distance_meters,
            "confidence": self.confidence,
            "confidence_band": self.confidence_band,
            "identification_method": self.identification_method,
            "source": self.source,
            "station_resolution_status": self.station_resolution_status.value,
            "price_model": self.price_model,
            "price_value_sek_kwh": self.price_value_sek_kwh,
            "candidates": [
                {
                    "score": c.score,
                    "label": c.label,
                    "provider_station_id": c.candidate.provider_station_id,
                    "operator": c.candidate.operator,
                    "station_name": c.candidate.station_name,
                    "distance_m": c.candidate.distance_m,
                }
                for c in self.candidates
            ],
            "selected_station_id": (
                self.selected_station.provider_station_id if self.selected_station else None
            ),
        }

    @classmethod
    def from_cache_dict(cls, data: dict) -> ResolvedChargingLocation:
        return cls(
            location_name=data.get("location_name") or "Unknown",
            station_name=data.get("station_name"),
            operator_name=data.get("operator_name"),
            charging_type=data.get("charging_type"),
            connector_type=data.get("connector_type"),
            max_power_kw=data.get("max_power_kw"),
            distance_meters=data.get("distance_meters"),
            confidence=int(data.get("confidence") or 0),
            confidence_band=data.get("confidence_band") or "UNKNOWN",
            identification_method=data.get("identification_method") or "UNKNOWN",
            source=data.get("source") or "CACHE",
            station_resolution_status=StationResolutionStatus(
                data.get("station_resolution_status") or "UNKNOWN"
            ),
            price_model=data.get("price_model") or "UNKNOWN",
            price_value_sek_kwh=data.get("price_value_sek_kwh"),
        )
