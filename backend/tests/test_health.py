import pytest


@pytest.mark.asyncio
async def test_health(client):
    ac, _, _ = client
    res = await ac.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
