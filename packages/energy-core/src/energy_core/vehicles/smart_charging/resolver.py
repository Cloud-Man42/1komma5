"""Resolve linked vehicle state for a charger."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import (
    VehicleHaloCorrelationModel,
    VehicleModel,
    VehicleProviderConnectionModel,
    VehicleStateLatestModel,
)
from energy_core.vehicles.smart_charging.models import VehicleChargingContext
from energy_core.vehicles.smart_charging.requirement import (
    compute_energy_requirement,
    departure_time_label,
    resolve_vehicle_deadline,
)

MIN_CORRELATION_CONFIDENCE = 0.5
TRUSTED_CORRELATION_STATUSES = frozenset({"ALIGNED", "PARTIAL"})
VEHICLE_STALE_SECONDS = 300.0


async def resolve_vehicle_charging_context(
    session: AsyncSession,
    *,
    site_id: int,
    charger_id: int,
    timezone: str,
    now: datetime | None = None,
) -> VehicleChargingContext | None:
    now = now or datetime.now(UTC)

    provider_enabled = await session.scalar(
        select(VehicleProviderConnectionModel.enabled).where(
            VehicleProviderConnectionModel.site_id == site_id,
            VehicleProviderConnectionModel.enabled.is_(True),
        )
    )
    if not provider_enabled:
        return None

    vehicle = await _find_vehicle(session, site_id=site_id, charger_id=charger_id)
    if vehicle is None or not vehicle.enabled:
        return None

    latest = await session.get(VehicleStateLatestModel, vehicle.id)
    correlation = await session.get(VehicleHaloCorrelationModel, vehicle.id)

    confidence = correlation.confidence if correlation else 0.0
    status = correlation.status if correlation else "UNAVAILABLE"
    data_age = _data_age_seconds(latest, now=now)
    stale = data_age > VEHICLE_STALE_SECONDS or (latest is not None and latest.data_quality == "STALE")
    correlation_ok = confidence >= MIN_CORRELATION_CONFIDENCE and status in TRUSTED_CORRELATION_STATUSES
    plugged_in = latest.is_plugged_in if latest else None
    active = correlation_ok and not stale and bool(plugged_in)

    requirement = compute_energy_requirement(
        current_soc_percent=latest.state_of_charge_percent if latest else None,
        target_soc_percent=latest.target_soc_percent if latest else None,
    )
    target_fraction = (
        latest.target_soc_percent / 100.0
        if latest and latest.target_soc_percent is not None
        else None
    )
    departure_label = departure_time_label(latest.departure_time if latest else None, timezone)
    deadline_at = resolve_vehicle_deadline(
        departure=latest.departure_time if latest else None,
        estimated_complete_at=latest.estimated_charge_complete_at if latest else None,
        timezone=timezone,
        now=now,
    )

    return VehicleChargingContext(
        vehicle_id=vehicle.id,
        display_name=vehicle.display_name or vehicle.model,
        provider=vehicle.provider,
        correlation_confidence=confidence,
        correlation_status=status,
        requirement=requirement,
        target_soc_fraction=target_fraction,
        departure_time=departure_label,
        deadline_at=deadline_at,
        estimated_complete_at=latest.estimated_charge_complete_at if latest else None,
        is_plugged_in=plugged_in,
        data_age_seconds=data_age,
        stale=stale,
        active=active,
    )


async def _find_vehicle(
    session: AsyncSession,
    *,
    site_id: int,
    charger_id: int,
) -> VehicleModel | None:
    result = await session.execute(
        select(VehicleModel).where(
            VehicleModel.site_id == site_id,
            VehicleModel.enabled.is_(True),
            VehicleModel.charger_id == charger_id,
        )
    )
    linked = list(result.scalars().all())
    if len(linked) == 1:
        return linked[0]
    if len(linked) > 1:
        return await _select_best_linked_vehicle(session, linked, charger_id=charger_id)

    result = await session.execute(
        select(VehicleModel).where(
            VehicleModel.site_id == site_id,
            VehicleModel.enabled.is_(True),
        )
    )
    vehicles = list(result.scalars().all())
    if len(vehicles) == 1:
        return vehicles[0]
    return None


async def _select_best_linked_vehicle(
    session: AsyncSession,
    vehicles: list[VehicleModel],
    *,
    charger_id: int,
) -> VehicleModel | None:
    """Pick the vehicle most likely active on this charger when several share charger_id."""
    now = datetime.now(UTC)
    best: VehicleModel | None = None
    best_score: tuple[int, int, float, float] | None = None

    for vehicle in vehicles:
        latest = await session.get(VehicleStateLatestModel, vehicle.id)
        correlation = await session.get(VehicleHaloCorrelationModel, vehicle.id)
        if correlation is not None and correlation.charger_id not in (None, charger_id):
            continue
        score = _vehicle_link_score(latest, correlation, now=now)
        if best_score is None or score > best_score:
            best = vehicle
            best_score = score

    return best or vehicles[0]


def _vehicle_link_score(
    latest: VehicleStateLatestModel | None,
    correlation: VehicleHaloCorrelationModel | None,
    *,
    now: datetime,
) -> tuple[int, int, float, float]:
    status = correlation.status if correlation else "UNAVAILABLE"
    status_rank = {
        "ALIGNED": 3,
        "PARTIAL": 2,
        "MISMATCH": 1,
        "UNAVAILABLE": 0,
    }.get(status, 0)
    plugged_rank = 1 if latest is not None and latest.is_plugged_in else 0
    confidence = correlation.confidence if correlation else 0.0
    data_age = _data_age_seconds(latest, now=now)
    freshness = -data_age if data_age != float("inf") else float("-inf")
    return (status_rank, plugged_rank, confidence, freshness)


def _data_age_seconds(latest: VehicleStateLatestModel | None, *, now: datetime) -> float:
    if latest is None:
        return float("inf")
    ts = latest.last_vehicle_update or latest.updated_at
    if ts is None:
        return float("inf")
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return max(0.0, (now - ts).total_seconds())
