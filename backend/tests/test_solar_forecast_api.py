from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from helpers import enable_solar_config, seed_readings, seed_recent_readings
from energy_core.solar_forecast.types import WeatherForecast, WeatherForecastPoint


def _sample_weather(site_id: int = 1) -> WeatherForecast:
    now = datetime.now(UTC)
    points = tuple(
        WeatherForecastPoint(
            timestamp=now + timedelta(minutes=15 * i),
            ghi_wm2=600.0,
            gti_wm2=550.0,
            cloud_cover_pct=20.0,
            temperature_c=18.0,
        )
        for i in range(16)
    )
    return WeatherForecast(
        site_id=site_id,
        fetched_at=now,
        provider="test",
        points=points,
        source="live",
    )


@pytest.mark.asyncio
async def test_solar_config_get_default_disabled(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/akarp/solar/config")
    assert res.status_code == 200
    body = res.json()
    assert body["enabled"] is False
    assert body["complete"] is False


@pytest.mark.asyncio
async def test_solar_config_enable_requires_fields(client):
    ac, _, _ = client
    res = await ac.put(
        "/api/sites/akarp/solar/config",
        json={"enabled": True},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_solar_config_put_persists(client):
    ac, _, _ = client
    body = await enable_solar_config(ac, "akarp")
    assert body["enabled"] is True
    assert body["complete"] is True
    assert body["latitude"] == 55.605

    again = await ac.get("/api/sites/akarp/solar/config")
    assert again.status_code == 200
    assert again.json()["enabled"] is True
    assert again.json()["latitude"] == 55.605


@pytest.mark.asyncio
async def test_solar_config_invalid_latitude(client):
    ac, _, _ = client
    res = await ac.put(
        "/api/sites/akarp/solar/config",
        json={
            "latitude": 999,
            "longitude": 13.0,
            "installed_peak_power_kw": 8,
            "enabled": True,
        },
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_solar_forecast_404_when_not_configured(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/akarp/solar/forecast")
    assert res.status_code == 404
    assert "Solprognos" in res.json()["detail"]


@pytest.mark.asyncio
async def test_solar_forecast_success_after_config(client, monkeypatch):
    ac, _, _ = client
    await enable_solar_config(ac, "akarp")

    with patch(
        "energy_core.solar_forecast.coordinator.OpenMeteoWeatherProvider.get_forecast",
        new=AsyncMock(return_value=_sample_weather()),
    ):
        res = await ac.get("/api/sites/akarp/solar/forecast")

    assert res.status_code == 200
    body = res.json()
    assert body["model_version"] == "solar-forecast-v2"
    assert body["expected_today_kwh"] >= 0
    assert body["forecast_so_far_kwh"] >= 0
    assert body["actual_today_kwh"] >= 0
    assert body["forecast_so_far_kwh"] <= body["expected_today_kwh"] + 0.001
    assert body["remaining_vs_expected_kwh"] == pytest.approx(
        max(0.0, body["expected_today_kwh"] - body["actual_today_kwh"]),
        abs=0.001,
    )
    assert len(body["points"]) > 0


@pytest.mark.asyncio
async def test_solar_forecast_today_alias(client, monkeypatch):
    ac, _, _ = client
    await enable_solar_config(ac, "akarp")
    with patch(
        "energy_core.solar_forecast.coordinator.OpenMeteoWeatherProvider.get_forecast",
        new=AsyncMock(return_value=_sample_weather()),
    ):
        res = await ac.get("/api/sites/akarp/solar/forecast/today")
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_solar_forecast_tomorrow_alias(client, monkeypatch):
    ac, _, _ = client
    await enable_solar_config(ac, "akarp")
    with patch(
        "energy_core.solar_forecast.coordinator.OpenMeteoWeatherProvider.get_forecast",
        new=AsyncMock(return_value=_sample_weather()),
    ):
        res = await ac.get("/api/sites/akarp/solar/forecast/tomorrow")
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_solar_accuracy_after_config(client, monkeypatch):
    ac, _, _ = client
    await enable_solar_config(ac, "akarp")
    with patch(
        "energy_core.solar_forecast.coordinator.OpenMeteoWeatherProvider.get_forecast",
        new=AsyncMock(return_value=_sample_weather()),
    ):
        await ac.get("/api/sites/akarp/solar/forecast")

    res = await ac.get("/api/sites/akarp/solar/accuracy")
    assert res.status_code == 200
    body = res.json()
    assert body["model_version"] == "solar-forecast-v2"
    assert body["site_slug"] == "akarp"


@pytest.mark.asyncio
async def test_solar_energy_budget_after_config(client, monkeypatch):
    ac, session_factory, settings = client
    await enable_solar_config(ac, "akarp")
    await seed_readings(
        session_factory,
        settings,
        "akarp",
        [(10, 0, 4000, 1500, 0, 2500, 60), (10, 5, 4200, 1600, 0, 2600, 61)],
    )
    with patch(
        "energy_core.solar_forecast.coordinator.OpenMeteoWeatherProvider.get_forecast",
        new=AsyncMock(return_value=_sample_weather()),
    ):
        await ac.get("/api/sites/akarp/solar/forecast")

    res = await ac.get("/api/sites/akarp/solar/energy-budget")
    assert res.status_code == 200
    body = res.json()
    assert body["site_slug"] == "akarp"
    assert body["forecast_solar_kwh"] >= 0


@pytest.mark.asyncio
async def test_solar_accuracy_zero_samples_null_metrics(client, monkeypatch):
    ac, _, _ = client
    await enable_solar_config(ac, "akarp")
    with patch(
        "energy_core.solar_forecast.coordinator.OpenMeteoWeatherProvider.get_forecast",
        new=AsyncMock(return_value=_sample_weather()),
    ):
        await ac.get("/api/sites/akarp/solar/forecast")

    res = await ac.get("/api/sites/akarp/solar/accuracy")
    assert res.status_code == 200
    body = res.json()
    assert body["metrics_insufficient"] is True
    assert body["model_state"] == "NO_DATA"
    assert body["historical_samples"] == 0
    assert body["mape_7d_pct"] is None
    assert body["mape_30d_pct"] is None
    assert body["mae_kwh_30d"] is None
    assert body["bias_pct_30d"] is None
    assert body["confidence_score"] is None


@pytest.mark.asyncio
async def test_solar_diagnostics_endpoint(client, monkeypatch):
    ac, _, _ = client
    await enable_solar_config(ac, "akarp")
    with patch(
        "energy_core.solar_forecast.coordinator.OpenMeteoWeatherProvider.get_forecast",
        new=AsyncMock(return_value=_sample_weather()),
    ):
        await ac.get("/api/sites/akarp/solar/forecast")

    res = await ac.get("/api/sites/akarp/solar/diagnostics")
    assert res.status_code == 200
    body = res.json()
    assert body["site_slug"] == "akarp"
    assert isinstance(body["observations"], list)


@pytest.mark.asyncio
async def test_solar_accuracy_learning_hides_metrics(client, monkeypatch):
    """With v2 profile in DB showing LEARNING, API must not expose misleading MAPE."""
    ac, session_factory, settings = client
    await enable_solar_config(ac, "akarp")
    with patch(
        "energy_core.solar_forecast.coordinator.OpenMeteoWeatherProvider.get_forecast",
        new=AsyncMock(return_value=_sample_weather()),
    ):
        await ac.get("/api/sites/akarp/solar/forecast")

    from energy_core.db.models import SolarForecastModelProfileModel
    from energy_core.db.repositories import SiteRepository

    async with session_factory() as session:
        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        session.add(
            SolarForecastModelProfileModel(
                site_id=site.id,
                model_version="solar-forecast-v2",
                historical_samples=1,
                model_state="LEARNING",
                mape_7d=100.0,
                mape_30d=100.0,
                bias_30d=-100.0,
                mae_30d=31.6,
                correction_factor=1.0,
                confidence_score=10.0,
            )
        )
        await session.commit()

    with patch(
        "app.api.solar_forecast._ensure_solar_observations_evaluated",
        new=AsyncMock(),
    ):
        res = await ac.get("/api/sites/akarp/solar/accuracy")
    assert res.status_code == 200
    body = res.json()
    assert body["model_state"] == "LEARNING"
    assert body["metrics_insufficient"] is True
    assert body["mape_7d_pct"] is None
    assert body["mape_30d_pct"] is None
    assert body["mae_kwh_30d"] is None
    assert body["bias_pct_30d"] is None
    assert body["confidence_score"] is None


@pytest.mark.asyncio
async def test_solar_forecast_includes_actual_vs_forecast_so_far(client, monkeypatch):
    ac, session_factory, settings = client
    await enable_solar_config(ac, "akarp")
    await seed_recent_readings(
        session_factory,
        settings,
        "akarp",
        [
            (5000, 1200, 0, 3800, 55),
            (5200, 1300, 0, 3900, 56),
        ],
    )
    with patch(
        "energy_core.solar_forecast.coordinator.OpenMeteoWeatherProvider.get_forecast",
        new=AsyncMock(return_value=_sample_weather()),
    ):
        res = await ac.get("/api/sites/akarp/solar/forecast")

    assert res.status_code == 200
    body = res.json()
    assert body["actual_today_kwh"] > 0
    assert body["forecast_so_far_kwh"] >= 0


@pytest.mark.asyncio
async def test_solar_accuracy_backfills_production_days(client):
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
    with patch(
        "energy_core.solar_forecast.coordinator.OpenMeteoWeatherProvider.get_forecast",
        new=AsyncMock(return_value=_sample_weather()),
    ):
        res = await ac.get("/api/sites/akarp/solar/accuracy")
    assert res.status_code == 200
    body = res.json()
    assert body["production_days_observed"] >= 1
    assert "historical_samples" in body
