"""Tests for vehicle-aware smart charging."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from energy_core.charging.config import ChargingConfig
from energy_core.charging.optimizer import (
    combined_charging_urgency,
    energy_charging_urgency,
)
from energy_core.db.models import (
    EvChargerModel,
    VehicleHaloCorrelationModel,
    VehicleModel,
    VehicleStateLatestModel,
)
from energy_core.energy.state import EnergyState
from energy_core.vehicles.smart_charging.enrichment import apply_vehicle_charging_context
from energy_core.vehicles.smart_charging.models import VehicleChargingContext, VehicleEnergyRequirement
from energy_core.vehicles.smart_charging.requirement import compute_energy_requirement
from energy_core.vehicles.smart_charging.resolver import (
    _select_best_linked_vehicle,
    _vehicle_link_score,
    resolve_vehicle_charging_context,
)


def test_compute_energy_requirement_from_soc_gap():
    req = compute_energy_requirement(current_soc_percent=47.0, target_soc_percent=80.0)
    assert req.required_energy_kwh == pytest.approx(29.7, rel=0.01)
    assert req.quality == "ESTIMATED"


def test_compute_energy_requirement_target_reached():
    req = compute_energy_requirement(current_soc_percent=82.0, target_soc_percent=80.0)
    assert req.required_energy_kwh == 0.0
    assert req.quality == "MEASURED"


def test_compute_energy_requirement_missing_soc():
    req = compute_energy_requirement(current_soc_percent=None, target_soc_percent=80.0)
    assert req.required_energy_kwh is None
    assert req.quality == "UNAVAILABLE"


def test_apply_vehicle_context_overrides_charger_prefs():
    charger = EvChargerModel(
        id=1,
        site_id=1,
        name="Halo",
        manufacturer="ChargeAmps",
        model="Halo",
        control_source="chargeamp",
        target_soc_pct=70.0,
        departure_time="06:00",
    )
    energy = EnergyState(timestamp=datetime.now(UTC), target_soc=0.6, departure_time="05:00")
    config = ChargingConfig(departure_time="06:00")
    context = VehicleChargingContext(
        vehicle_id=9,
        display_name="Mercedes EQE",
        provider="mercedes",
        correlation_confidence=0.9,
        correlation_status="ALIGNED",
        requirement=VehicleEnergyRequirement(
            current_soc_percent=47.0,
            target_soc_percent=80.0,
            required_energy_kwh=29.7,
            battery_capacity_kwh=90.0,
            quality="ESTIMATED",
        ),
        target_soc_fraction=0.8,
        departure_time="07:30",
        deadline_at=datetime(2026, 8, 24, 5, 30, tzinfo=UTC),
        estimated_complete_at=None,
        is_plugged_in=True,
        data_age_seconds=10.0,
        stale=False,
        active=True,
    )

    enriched_energy, enriched_config = apply_vehicle_charging_context(charger, energy, config, context)

    assert enriched_energy.target_soc == pytest.approx(0.8)
    assert enriched_energy.departure_time == "07:30"
    assert enriched_energy.ev_soc == pytest.approx(0.47)
    assert enriched_energy.vehicle_required_energy_kwh == pytest.approx(29.7)
    assert enriched_energy.vehicle_linked is True
    assert enriched_config.departure_time == "07:30"


def test_apply_vehicle_context_inactive_is_noop():
    charger = EvChargerModel(
        id=1,
        site_id=1,
        name="Halo",
        manufacturer="ChargeAmps",
        model="Halo",
        control_source="chargeamp",
    )
    energy = EnergyState(timestamp=datetime.now(UTC), target_soc=0.6)
    config = ChargingConfig()
    context = VehicleChargingContext(
        vehicle_id=9,
        display_name="Mercedes EQE",
        provider="mercedes",
        correlation_confidence=0.2,
        correlation_status="MISMATCH",
        requirement=compute_energy_requirement(current_soc_percent=47.0, target_soc_percent=80.0),
        target_soc_fraction=0.8,
        departure_time="07:30",
        deadline_at=None,
        estimated_complete_at=None,
        is_plugged_in=True,
        data_age_seconds=10.0,
        stale=False,
        active=False,
    )

    enriched_energy, enriched_config = apply_vehicle_charging_context(charger, energy, config, context)
    assert enriched_energy.target_soc == 0.6
    assert enriched_energy.vehicle_linked is False
    assert enriched_config.departure_time is None


def test_energy_charging_urgency_tight_deadline():
    assert energy_charging_urgency(required_energy_kwh=30.0, hours_left=2.0, charge_power_kw=11.0) == 1.0


def test_energy_charging_urgency_relaxed():
    assert energy_charging_urgency(required_energy_kwh=5.0, hours_left=12.0, charge_power_kw=11.0) == 0.0


def test_combined_charging_urgency_uses_max():
    now = datetime(2026, 8, 23, 20, 0, tzinfo=UTC)
    config = ChargingConfig(smart_charge_hours=4.0)
    deadline = now + timedelta(hours=12)
    urgency = combined_charging_urgency(
        now,
        deadline=deadline,
        config=config,
        required_energy_kwh=35.0,
    )
    assert urgency > 0.0


@pytest.mark.asyncio
async def test_resolve_vehicle_context_active_when_aligned():
    session = AsyncMock()
    vehicle = VehicleModel(
        id=3,
        site_id=1,
        provider="mercedes",
        external_id="eqe",
        manufacturer="Mercedes-Benz",
        model="EQE 500",
        display_name="EQE",
        enabled=True,
        charger_id=4,
    )
    latest = VehicleStateLatestModel(
        vehicle_id=3,
        state_of_charge_percent=47.0,
        target_soc_percent=80.0,
        is_plugged_in=True,
        data_quality="MEASURED",
        last_vehicle_update=datetime.now(UTC),
    )
    correlation = VehicleHaloCorrelationModel(
        vehicle_id=3,
        charger_id=4,
        confidence=0.92,
        status="ALIGNED",
    )

    async def scalar_side_effect(stmt):
        return True

    async def execute_side_effect(stmt):
        result = MagicMock()
        result.scalars.return_value.all.return_value = [vehicle]
        return result

    session.scalar = AsyncMock(side_effect=scalar_side_effect)
    session.execute = AsyncMock(side_effect=execute_side_effect)
    session.get = AsyncMock(
        side_effect=lambda model, pk: latest
        if pk == 3 and model is VehicleStateLatestModel
        else correlation
        if pk == 3 and model is VehicleHaloCorrelationModel
        else None
    )

    context = await resolve_vehicle_charging_context(
        session,
        site_id=1,
        charger_id=4,
        timezone="Europe/Stockholm",
    )
    assert context is not None
    assert context.active is True
    assert context.requirement.required_energy_kwh == pytest.approx(29.7, rel=0.01)


@pytest.mark.asyncio
async def test_resolve_vehicle_context_none_when_integration_disabled():
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=None)

    context = await resolve_vehicle_charging_context(
        session,
        site_id=1,
        charger_id=4,
        timezone="Europe/Stockholm",
    )
    assert context is None


def test_vehicle_link_score_prefers_aligned_plugged_vehicle():
    now = datetime(2026, 8, 23, 20, 0, tzinfo=UTC)
    eqe_latest = VehicleStateLatestModel(
        vehicle_id=2,
        state_of_charge_percent=89.0,
        is_plugged_in=True,
        data_quality="MEASURED",
        last_vehicle_update=now,
    )
    eqe_correlation = VehicleHaloCorrelationModel(
        vehicle_id=2,
        charger_id=4,
        confidence=1.0,
        status="ALIGNED",
    )
    glc_latest = VehicleStateLatestModel(
        vehicle_id=1,
        state_of_charge_percent=0.0,
        is_plugged_in=False,
        data_quality="UNKNOWN",
        last_vehicle_update=now - timedelta(hours=2),
    )
    glc_correlation = VehicleHaloCorrelationModel(
        vehicle_id=1,
        charger_id=4,
        confidence=0.0,
        status="UNAVAILABLE",
    )

    eqe_score = _vehicle_link_score(eqe_latest, eqe_correlation, now=now)
    glc_score = _vehicle_link_score(glc_latest, glc_correlation, now=now)
    assert eqe_score > glc_score


@pytest.mark.asyncio
async def test_select_best_linked_vehicle_when_multiple_share_charger():
    session = AsyncMock()
    glc = VehicleModel(id=1, site_id=1, provider="mercedes", enabled=True, charger_id=4)
    eqe = VehicleModel(id=2, site_id=1, provider="mercedes", enabled=True, charger_id=4)
    now = datetime(2026, 8, 23, 20, 0, tzinfo=UTC)

    async def get_side_effect(model, pk):
        if model is VehicleStateLatestModel:
            if pk == 1:
                return VehicleStateLatestModel(
                    vehicle_id=1,
                    is_plugged_in=False,
                    data_quality="UNKNOWN",
                    last_vehicle_update=now - timedelta(hours=2),
                )
            if pk == 2:
                return VehicleStateLatestModel(
                    vehicle_id=2,
                    state_of_charge_percent=89.0,
                    is_plugged_in=True,
                    data_quality="MEASURED",
                    last_vehicle_update=now,
                )
        if model is VehicleHaloCorrelationModel:
            if pk == 1:
                return VehicleHaloCorrelationModel(vehicle_id=1, charger_id=4, confidence=0.0, status="UNAVAILABLE")
            if pk == 2:
                return VehicleHaloCorrelationModel(vehicle_id=2, charger_id=4, confidence=1.0, status="ALIGNED")
        return None

    session.get = AsyncMock(side_effect=get_side_effect)

    selected = await _select_best_linked_vehicle(session, [glc, eqe], charger_id=4)
    assert selected is not None
    assert selected.id == 2
