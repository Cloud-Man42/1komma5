"""Integration health API tests."""

import pytest


@pytest.mark.asyncio
async def test_integration_health_empty_for_new_site(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/akarp/integration-health")
    assert res.status_code == 200
    body = res.json()
    assert body["slug"] == "akarp"
    assert isinstance(body["providers"], list)


@pytest.mark.asyncio
async def test_integration_health_404_unknown_site(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/no-such-site/integration-health")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_integration_health_returns_provider_rows(client):
    ac, session_factory, settings = client
    from energy_core.db.repositories import SiteRepository
    from energy_core.integrations.health import IntegrationHealthRecorder

    async with session_factory() as session:
        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        recorder = IntegrationHealthRecorder(session, is_sqlite=settings.is_sqlite)
        await recorder.record_success(site.id, "heartbeat", latency_ms=42.0)
        await session.commit()

    res = await ac.get("/api/sites/akarp/integration-health")
    assert res.status_code == 200
    body = res.json()
    assert len(body["providers"]) == 1
    assert body["providers"][0]["provider"] == "heartbeat"
    assert body["providers"][0]["status"] == "ok"
