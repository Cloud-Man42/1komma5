from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from helpers import enable_solar_config, seed_readings
from energy_core.solar_forecast.types import SolarForecastObservation


@pytest.mark.asyncio
async def test_solar_performance_404_when_not_configured(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/akarp/solar/performance")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_solar_performance_builds_from_observations(client, monkeypatch):
    ac, session_factory, settings = client
    await enable_solar_config(ac, "akarp")

    yesterday = datetime.now(UTC).date() - timedelta(days=1)
    dense_readings = [
        (hour, minute, 5000, 1500, 0, 3500, 60)
        for hour in range(8, 18)
        for minute in (0, 15, 30, 45)
    ]
    await seed_readings(
        session_factory,
        settings,
        "akarp",
        dense_readings,
        day=yesterday.day,
        month=yesterday.month,
        year=yesterday.year,
    )

    observations = [
        SolarForecastObservation(
            site_id=1,
            forecast_date=yesterday - timedelta(days=offset),
            forecast_kwh_raw=20.0,
            forecast_kwh_corrected=18.0,
            actual_kwh=18.0,
            training_eligible=True,
            model_version="solar-forecast-v2",
        )
        for offset in (1, 2)
    ]

    with patch(
        "energy_core.solar_forecast.coordinator.SolarForecastCoordinator.evaluate_site_observations",
        new=AsyncMock(),
    ), patch(
        "energy_core.db.solar_intelligence_repo.SolarPerformanceDailyRepository.list_for_site",
        new=AsyncMock(return_value=[]),
    ), patch(
        "energy_core.db.solar_forecast_repo.SolarForecastObservationRepository.list_for_site",
        new=AsyncMock(return_value=observations),
    ), patch(
        "energy_core.db.solar_forecast_repo.SolarForecastRepository.get_latest",
        new=AsyncMock(return_value=None),
    ):
        res = await ac.get("/api/sites/akarp/solar/performance")

    assert res.status_code == 200
    body = res.json()
    assert body["site_slug"] == "akarp"
    assert len(body["days"]) == 2
    assert body["days"][0]["performance_ratio"] == 1.0
    assert body["headline_ratio"] == 1.0
    assert body["week_avg"] == 1.0
