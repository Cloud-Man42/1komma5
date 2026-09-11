"""Security review regression tests for admin authentication."""

from __future__ import annotations

import pytest
from app.deps import set_session_factory
from app.main import create_app
from energy_core.config import Settings
from energy_core.db.models import Base, SiteModel, VehicleModel, VehicleStateLatestModel
from energy_core.db.session import create_engine, create_session_factory
from energy_core.seed import seed_sites
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select


@pytest.fixture
async def secured_client(tmp_path):
    db_file = tmp_path / "security-auth.db"
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}",
        EMIC_ADMIN_TOKEN="admin-secret",
    )
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        await seed_sites(session)
        await session.commit()

    app = create_app(settings)
    set_session_factory(session_factory, settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, session_factory
    await engine.dispose()


def _historical_energy_payload() -> dict:
    return {
        "source": "security-test",
        "estimated": True,
        "months": [{"month": month, "imported_kwh": 100.0} for month in range(1, 13)],
    }


@pytest.mark.asyncio
async def test_anonymous_site_list_returns_401_when_admin_token_set(secured_client) -> None:
    ac, _ = secured_client
    response = await ac.get("/api/sites")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_anonymous_vehicle_list_returns_401_when_admin_token_set(secured_client) -> None:
    ac, _ = secured_client
    response = await ac.get("/api/sites/akarp/vehicles")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_vehicle_gps_not_disclosed_without_auth(secured_client) -> None:
    ac, session_factory = secured_client
    async with session_factory() as session:
        from datetime import UTC, datetime

        from energy_core.db.models import SiteModel

        site_row = (await session.execute(select(SiteModel).where(SiteModel.slug == "akarp"))).scalar_one()
        vehicle = VehicleModel(
            site_id=site_row.id,
            provider="mercedes",
            external_id="ev-gps",
            display_name="GPS EV",
            enabled=True,
        )
        session.add(vehicle)
        await session.flush()
        session.add(
            VehicleStateLatestModel(
                vehicle_id=vehicle.id,
                latitude=12.345,
                longitude=67.89,
                location_updated_at=datetime.now(UTC),
            )
        )
        await session.commit()

    unauth = await ac.get("/api/sites/akarp/vehicles")
    assert unauth.status_code == 401
    assert "12.345" not in unauth.text

    authed = await ac.get(
        "/api/sites/akarp/vehicles",
        headers={"Authorization": "Bearer admin-secret"},
    )
    assert authed.status_code == 200
    vehicles = authed.json()["vehicles"]
    assert any(v.get("latitude") == 12.345 for v in vehicles)


@pytest.mark.asyncio
async def test_bridge_settings_patch_requires_auth(secured_client) -> None:
    ac, _ = secured_client
    unauth = await ac.patch(
        "/api/sites/akarp/heartbeat/bridge/settings",
        json={"simulation_mode": False},
    )
    assert unauth.status_code == 401

    authed = await ac.patch(
        "/api/sites/akarp/heartbeat/bridge/settings",
        json={"simulation_mode": False},
        headers={"Authorization": "Bearer admin-secret"},
    )
    assert authed.status_code == 200
    assert authed.json()["simulation_mode"] is False


@pytest.mark.asyncio
async def test_historical_energy_put_requires_auth(secured_client) -> None:
    ac, _ = secured_client
    unauth = await ac.put(
        "/api/sites/akarp/historical-energy/2025",
        json=_historical_energy_payload(),
    )
    assert unauth.status_code == 401

    authed = await ac.put(
        "/api/sites/akarp/historical-energy/2025",
        json=_historical_energy_payload(),
        headers={"Authorization": "Bearer admin-secret"},
    )
    assert authed.status_code == 200
    assert authed.json()["source"] == "security-test"


@pytest.mark.asyncio
async def test_solar_config_put_requires_auth(secured_client) -> None:
    ac, _ = secured_client
    unauth = await ac.put(
        "/api/sites/akarp/solar/config",
        json={"enabled": True},
    )
    assert unauth.status_code == 401


@pytest.mark.asyncio
async def test_orchestration_priorities_put_requires_auth(secured_client) -> None:
    ac, _ = secured_client
    unauth = await ac.put(
        "/api/sites/akarp/energy/orchestration/priorities",
        json={"loads": [{"load_id": "spa", "priority": 1}]},
    )
    assert unauth.status_code == 401
