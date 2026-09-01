"""Station candidate scoring and multi-match handling."""

from __future__ import annotations

from energy_core.integrations.charging_stations.models import (
    ChargingStationCandidate,
    ResolvedChargingLocation,
    StationCandidateScore,
    StationResolutionStatus,
)
from energy_core.vehicles.charging_intelligence.correlation import confidence_band
from energy_core.vehicles.charging_intelligence.location import (
    ConfidenceBand,
    IdentificationMethod,
)


MULTI_MATCH_GAP = 15


def format_operator_label(confidence_band_value: str, operator: str | None) -> str | None:
    if not operator:
        return None
    if confidence_band_value in {ConfidenceBand.LOW.value, ConfidenceBand.MEDIUM.value, ConfidenceBand.UNKNOWN.value}:
        return f"Likely {operator}"
    return operator


def score_candidates(
    candidates: list[ChargingStationCandidate],
    *,
    expected_operator: str | None = None,
    expected_charging_type: str | None = None,
    vehicle_charging_type: str | None = None,
    vehicle_charging_power_kw: float | None = None,
    user_confirmed_ids: set[str] | None = None,
    previous_station_ids: set[str] | None = None,
    geofence_match: bool = False,
    direct_charger_correlation: bool = False,
) -> list[StationCandidateScore]:
    confirmed = user_confirmed_ids or set()
    previous = previous_station_ids or set()
    scored: list[StationCandidateScore] = []
    for candidate in candidates:
        score = _score_one(
            candidate,
            expected_operator=expected_operator,
            expected_charging_type=expected_charging_type,
            vehicle_charging_type=vehicle_charging_type,
            vehicle_charging_power_kw=vehicle_charging_power_kw,
            user_confirmed=candidate.provider_station_id in confirmed,
            previous_match=candidate.provider_station_id in previous,
            geofence_match=geofence_match,
            direct_charger_correlation=direct_charger_correlation,
        )
        label = _candidate_label(candidate)
        scored.append(StationCandidateScore(candidate=candidate, score=score, label=label))
    scored.sort(key=lambda item: item.score, reverse=True)
    return scored


def resolve_from_scores(
    scored: list[StationCandidateScore],
    *,
    location_name: str,
    identification_method: str,
    source: str,
    geofence_match: bool = False,
) -> ResolvedChargingLocation:
    if not scored:
        return _unknown(location_name=location_name, identification_method=identification_method, source=source)

    top = scored[0]
    second = scored[1] if len(scored) > 1 else None
    if second is not None and (top.score - second.score) <= MULTI_MATCH_GAP and top.score < 85:
        band = ConfidenceBand.LOW
        return ResolvedChargingLocation(
            location_name=location_name,
            station_name=None,
            operator_name=None,
            charging_type=None,
            connector_type=None,
            max_power_kw=None,
            distance_meters=top.candidate.distance_m,
            confidence=top.score,
            confidence_band=band.value,
            identification_method=IdentificationMethod.MULTIPLE_CANDIDATES.value,
            source=source,
            station_resolution_status=StationResolutionStatus.MULTIPLE_CANDIDATES,
            candidates=scored[:5],
            selected_station=None,
            price_model=top.candidate.price_model,
            price_value_sek_kwh=top.candidate.price_value_sek_kwh,
        )

    band = confidence_band(top.score)
    operator = format_operator_label(band.value, top.candidate.operator)
    station_name = top.candidate.station_name
    if station_name and operator:
        display_name = f"{operator} – {station_name}"
    elif station_name:
        display_name = station_name
    elif operator:
        display_name = operator
    else:
        display_name = location_name

    status = StationResolutionStatus.OK if top.score >= 60 else StationResolutionStatus.DEGRADED
    if geofence_match and top.score >= 70:
        method = IdentificationMethod.CHARGEFINDER_AND_GEOFENCE.value
    else:
        method = identification_method

    return ResolvedChargingLocation(
        location_name=display_name if not geofence_match else location_name,
        station_name=station_name,
        operator_name=operator,
        charging_type=top.candidate.charging_type,
        connector_type=top.candidate.connector_type,
        max_power_kw=top.candidate.max_power_kw,
        distance_meters=top.candidate.distance_m,
        confidence=top.score,
        confidence_band=band.value,
        identification_method=method,
        source=source,
        station_resolution_status=status,
        candidates=scored[:5],
        selected_station=top.candidate,
        price_model=top.candidate.price_model,
        price_value_sek_kwh=top.candidate.price_value_sek_kwh,
    )


def _score_one(
    candidate: ChargingStationCandidate,
    *,
    expected_operator: str | None,
    expected_charging_type: str | None,
    vehicle_charging_type: str | None,
    vehicle_charging_power_kw: float | None,
    user_confirmed: bool,
    previous_match: bool,
    geofence_match: bool,
    direct_charger_correlation: bool,
) -> int:
    score = 0
    distance = candidate.distance_m or 9999
    if distance < 30:
        score += 40
    elif distance < 75:
        score += 30
    elif distance < 150:
        score += 20

    if geofence_match:
        score += 40
    if direct_charger_correlation:
        score += 50

    if expected_operator and candidate.operator:
        if _operators_match(expected_operator, candidate.operator):
            score += 30

    if previous_match:
        score += 30
    if user_confirmed:
        score += 50

    if candidate.connector_type and expected_charging_type:
        score += 15

    if vehicle_charging_power_kw is not None and candidate.max_power_kw is not None:
        if abs(candidate.max_power_kw - vehicle_charging_power_kw) <= 5:
            score += 10

    if expected_charging_type and candidate.charging_type == expected_charging_type:
        score += 10
    if vehicle_charging_type and candidate.charging_type == vehicle_charging_type:
        score += 5

    return min(score, 100)


def _operators_match(expected: str, actual: str) -> bool:
    a = expected.lower().strip()
    b = actual.lower().strip()
    return a in b or b in a


def _candidate_label(candidate: ChargingStationCandidate) -> str:
    name = candidate.station_name or candidate.operator or candidate.provider_station_id
    distance = int(candidate.distance_m or 0)
    return f"{name} – {distance} m"


def _unknown(*, location_name: str, identification_method: str, source: str) -> ResolvedChargingLocation:
    return ResolvedChargingLocation(
        location_name=location_name,
        station_name=None,
        operator_name=None,
        charging_type=None,
        connector_type=None,
        max_power_kw=None,
        distance_meters=None,
        confidence=0,
        confidence_band=ConfidenceBand.UNKNOWN.value,
        identification_method=identification_method,
        source=source,
        station_resolution_status=StationResolutionStatus.UNKNOWN,
    )
