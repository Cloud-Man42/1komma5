"""Characterization tests for endpoints affected by modular Step 1 symbol moves."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from energy_core.contracts.telemetry import STALE_TELEMETRY_SECONDS
from energy_core.db.models import VehicleModel, VehicleProviderConnectionModel, VehicleStateLatestModel


@pytest.mark.asyncio
async def test_stale_telemetry_threshold_characterization() -> None:
    """Document the canonical stale threshold used by dashboard and vehicle paths."""
    assert STALE_TELEMETRY_SECONDS == 300


@pytest.mark.asyncio
async def test_dashboard_vehicle_section_marks_stale_data(client):
    ac, session_factory, _settings = client
    async with session_factory() as session:
        from energy_core.db.repositories import SiteRepository

        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        session.add(
            VehicleProviderConnectionModel(
                site_id=site.id,
                provider="mercedes",
                enabled=True,
                username="user@example.com",
            )
        )
        vehicle = VehicleModel(
            site_id=site.id,
            provider="mercedes",
            external_id="test-veh",
            display_name="Test EV",
            enabled=True,
        )
        session.add(vehicle)
        await session.flush()
        stale_ts = datetime.now(UTC) - timedelta(seconds=STALE_TELEMETRY_SECONDS + 30)
        session.add(
            VehicleStateLatestModel(
                vehicle_id=vehicle.id,
                state_of_charge_percent=55.0,
                is_plugged_in=True,
                is_charging=False,
                connection_state="CONNECTED",
                data_quality="MEASURED",
                last_vehicle_update=stale_ts,
            )
        )
        await session.commit()

    response = await ac.get("/api/sites/akarp/dashboard")
    assert response.status_code == 200
    vehicle = response.json()["vehicle"]
    assert vehicle["available"] is True
    assert vehicle["freshness_label"] == "INAKTUELL"


@pytest.mark.asyncio
async def test_vehicle_api_marks_stale_label(client):
    ac, session_factory, _settings = client
    async with session_factory() as session:
        from energy_core.db.repositories import SiteRepository

        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        vehicle = VehicleModel(
            site_id=site.id,
            provider="mercedes",
            external_id="test-veh-2",
            display_name="Test EV 2",
            enabled=True,
        )
        session.add(vehicle)
        await session.flush()
        session.add(
            VehicleStateLatestModel(
                vehicle_id=vehicle.id,
                state_of_charge_percent=70.0,
                connection_state="CONNECTED",
                data_quality="STALE",
            )
        )
        await session.commit()
        vehicle_id = vehicle.id

    response = await ac.get(f"/api/sites/akarp/vehicles/{vehicle_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == vehicle_id
    assert body["freshness_label"] == "INAKTUELL"
