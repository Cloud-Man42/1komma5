"""API tests for horizon optimizer."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from energy_core.energy_optimizer.horizon import HorizonLoadRecommendation, HorizonOptimizerSnapshot


def _snapshot(**overrides) -> HorizonOptimizerSnapshot:
    base = dict(
        available=True,
        monitor_only=True,
        horizon_hours=48,
        horizon_blocks=96,
        generated_at=datetime(2026, 9, 4, 8, 0, tzinfo=UTC),
        total_planned_savings_sek=5.5,
        headline_sv="Koordinerad 48h-plan för 1 laster",
        summary_sv="Beräknad besparing: 5.50 kr.",
        loads=(
            HorizonLoadRecommendation(
                load_id="ev_charger_1",
                name="Garage EV",
                load_type="ev",
                priority=60,
                strategy="SMART",
                window_start=datetime(2026, 9, 4, 10, 0, tzinfo=UTC),
                window_end=datetime(2026, 9, 4, 12, 0, tzinfo=UTC),
                expected_energy_kwh=6.0,
                expected_cost_sek=12.0,
                expected_energy_source="SOLAR",
                savings_sek=5.5,
                reason_sv="smart",
                explanation_sv="Billigt fönster",
            ),
        ),
    )
    base.update(overrides)
    return HorizonOptimizerSnapshot(**base)


@pytest.mark.asyncio
async def test_horizon_optimizer_returns_plan(client) -> None:
    ac, _, _ = client
    with patch(
        "energy_core.site_energy.orchestrator_service.SiteEnergyOrchestratorService.plan_horizon_readonly",
        new=AsyncMock(return_value=_snapshot()),
    ):
        res = await ac.get("/api/sites/akarp/horizon-optimizer")

    assert res.status_code == 200
    body = res.json()
    assert body["slug"] == "akarp"
    assert body["available"] is True
    assert body["monitor_only"] is True
    assert body["horizon_blocks"] == 96
    assert len(body["loads"]) == 1
    assert body["loads"][0]["load_type"] == "ev"
    assert body["battery"] is not None


@pytest.mark.asyncio
async def test_horizon_optimizer_site_not_found(client) -> None:
    ac, _, _ = client
    res = await ac.get("/api/sites/missing/horizon-optimizer")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_horizon_optimizer_unavailable_without_loads(client) -> None:
    ac, _, _ = client
    with patch(
        "energy_core.site_energy.orchestrator_service.SiteEnergyOrchestratorService.plan_horizon_readonly",
        new=AsyncMock(
            return_value=_snapshot(
                available=False,
                loads=(),
                headline_sv=None,
                summary_sv=None,
                unavailable_reason_sv="Inga flexibla laster är konfigurerade på siten.",
            )
        ),
    ):
        res = await ac.get("/api/sites/akarp/horizon-optimizer")

    assert res.status_code == 200
    body = res.json()
    assert body["available"] is False
    assert body["unavailable_reason_sv"] is not None


@pytest.mark.asyncio
async def test_horizon_optimizer_uses_redis_cache_on_second_request(client) -> None:
    from unittest.mock import AsyncMock, patch

    from energy_core.cache.service import reset_cache_service

    ac, _, _ = client
    reset_cache_service()
    cached_payload = {
        "slug": "akarp",
        "timezone": "Europe/Stockholm",
        "available": True,
        "monitor_only": True,
        "unavailable_reason_sv": None,
        "horizon_hours": 48,
        "horizon_blocks": 96,
        "generated_at": "2026-09-04T08:00:00Z",
        "total_planned_savings_sek": 5.5,
        "headline_sv": "Cached",
        "summary_sv": "Cached summary",
        "loads": [],
        "battery": None,
    }
    cache = AsyncMock()
    cache.get = AsyncMock(side_effect=[None, cached_payload])
    cache.get_or_set = AsyncMock(return_value=cached_payload)

    with patch(
        "energy_core.site_energy.orchestrator_service.SiteEnergyOrchestratorService.plan_horizon_readonly",
        new=AsyncMock(return_value=_snapshot()),
    ), patch("app.api.horizon_optimizer.get_cache_service", return_value=cache):
        first = await ac.get("/api/sites/akarp/horizon-optimizer")
        second = await ac.get("/api/sites/akarp/horizon-optimizer")

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["headline_sv"] == "Cached"
    cache.get_or_set.assert_awaited_once()
