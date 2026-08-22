"""Tests for solar smart charging planner."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from energy_core.charging.solar_plan import build_solar_charging_plan, planning_factor
from energy_core.solar_forecast.types import SolarForecast, SolarForecastPoint


def _forecast(*, remaining_kwh: float = 15.0, quality: str = "HIGH") -> SolarForecast:
    now = datetime(2026, 6, 15, 8, 0, tzinfo=UTC)
    points = tuple(
        SolarForecastPoint(
            timestamp=now + timedelta(hours=h),
            baseline_power_w=4000.0,
            corrected_power_w=4000.0,
            expected_energy_kwh=remaining_kwh / 8,
            lower_bound_power_w=3000.0,
            upper_bound_power_w=5000.0,
            confidence=0.9,
        )
        for h in range(8)
    )
    return SolarForecast(
        site_id=1,
        generated_at=now,
        model_version="solar-forecast-v1",
        quality=quality,  # type: ignore[arg-type]
        weather_source="live",
        expected_today_kwh=remaining_kwh,
        remaining_today_kwh=remaining_kwh,
        expected_tomorrow_kwh=None,
        peak_power_w=5000.0,
        peak_time=now + timedelta(hours=4),
        confidence=0.9,
        lower_today_kwh=remaining_kwh * 0.8,
        upper_today_kwh=remaining_kwh * 1.2,
        weather_summary="Sol förhållanden: bra",
        points=points,
    )


def test_scenario_a_wait_for_solar() -> None:
    now = datetime(2026, 6, 15, 8, 0, tzinfo=UTC)
    plan = build_solar_charging_plan(
        forecast=_forecast(remaining_kwh=15.0),
        ev_required_kwh=10.0,
        deadline=now + timedelta(hours=10),
        now=now,
        timezone="Europe/Stockholm",
    )
    assert plan.planned_grid_kwh <= 0.01
    assert plan.reason_code == "solar_forecast_wait"


def test_scenario_b_partial_grid() -> None:
    now = datetime(2026, 6, 15, 8, 0, tzinfo=UTC)
    plan = build_solar_charging_plan(
        forecast=_forecast(remaining_kwh=8.0),
        ev_required_kwh=20.0,
        deadline=now + timedelta(hours=10),
        now=now,
        timezone="Europe/Stockholm",
    )
    assert plan.planned_grid_kwh > 10.0
    assert plan.reason_code == "solar_forecast_partial_grid"


def test_confidence_adjustment() -> None:
    assert planning_factor("HIGH") == 0.95
    assert planning_factor("LOW") == 0.60


@pytest.mark.asyncio
async def test_load_solar_charging_plan_returns_none_without_required_energy():
    from energy_core.config import Settings
    from energy_core.db.models import Base
    from energy_core.db.repositories import SiteRepository
    from energy_core.db.ev_charger_repo import EvChargerRepository
    from energy_core.db.session import create_engine, create_session_factory
    from energy_core.charging.solar_plan import load_solar_charging_plan_for_charger

    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL="sqlite+aiosqlite:///:memory:")
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        site = await SiteRepository(session).upsert_site("akarp", "Åkarp", "Europe/Stockholm")
        charger_repo = EvChargerRepository(session)
        charger = await charger_repo.create(
            site.id,
            name="Halo",
            manufacturer="ChargeAmps",
            model="Halo",
            control_source="chargeamp",
        )
        await session.commit()

        plan = await load_solar_charging_plan_for_charger(session, site, charger)
        assert plan is None
    await engine.dispose()


@pytest.mark.asyncio
async def test_load_solar_charging_plan_without_forecast():
    from energy_core.config import Settings
    from energy_core.db.models import Base
    from energy_core.db.repositories import SiteRepository
    from energy_core.db.ev_charger_repo import EvChargerRepository
    from energy_core.db.session import create_engine, create_session_factory
    from energy_core.charging.solar_plan import load_solar_charging_plan_for_charger

    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL="sqlite+aiosqlite:///:memory:")
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        site = await SiteRepository(session).upsert_site("akarp", "Åkarp", "Europe/Stockholm")
        charger_repo = EvChargerRepository(session)
        charger = await charger_repo.create(
            site.id,
            name="Halo",
            manufacturer="ChargeAmps",
            model="Halo",
            control_source="chargeamp",
            required_energy_kwh=10.0,
            departure_time="07:00",
        )
        await session.commit()

        now = datetime(2026, 6, 15, 8, 0, tzinfo=UTC)
        plan = await load_solar_charging_plan_for_charger(session, site, charger, now=now)
        assert plan is not None
        assert plan.reason_code == "solar_forecast_unavailable"
        assert plan.planned_grid_kwh == 10.0
    await engine.dispose()
