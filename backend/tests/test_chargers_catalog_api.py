import pytest


@pytest.mark.asyncio
async def test_list_charger_manufacturers(client):
    ac, _, _ = client
    res = await ac.get("/api/chargers/manufacturers")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 20
    assert any(item["id"] == "charge-amps" for item in data)


@pytest.mark.asyncio
async def test_list_charger_models(client):
    ac, _, _ = client
    res = await ac.get("/api/chargers/manufacturers/charge-amps/models")
    assert res.status_code == 200
    data = res.json()
    assert any(item["id"] == "halo" for item in data)
    halo = next(item for item in data if item["id"] == "halo")
    assert halo["status"] == "FULL"


@pytest.mark.asyncio
async def test_charger_model_detail(client):
    ac, _, _ = client
    res = await ac.get("/api/chargers/manufacturers/charge-amps/models/halo")
    assert res.status_code == 200
    body = res.json()
    assert body["model"]["id"] == "halo"
    assert len(body["integration_methods"]) >= 1


@pytest.mark.asyncio
async def test_feature_matrix(client):
    ac, _, _ = client
    res = await ac.get("/api/chargers/feature-matrix")
    assert res.status_code == 200
    rows = res.json()
    assert len(rows) > 0
    assert "manufacturer" in rows[0]


@pytest.mark.asyncio
async def test_get_charger_manufacturer(client):
    ac, _, _ = client
    res = await ac.get("/api/chargers/manufacturers/zaptec")
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == "zaptec"
    assert body["model_count"] >= 1


@pytest.mark.asyncio
async def test_list_integration_methods(client):
    ac, _, _ = client
    res = await ac.get("/api/chargers/integration-methods")
    assert res.status_code == 200
    methods = res.json()
    assert len(methods) >= 20
    assert any(item["id"] == "CHARGE_AMPS_CLOUD" for item in methods)
    assert any(item["id"] == "ZAPTEC_REST" for item in methods)
    charge_amps = next(item for item in methods if item["id"] == "CHARGE_AMPS_CLOUD")
    assert charge_amps["implementation_status"] == "FULL"


@pytest.mark.asyncio
async def test_unknown_manufacturer_404(client):
    ac, _, _ = client
    res = await ac.get("/api/chargers/manufacturers/unknown-vendor/models")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_get_unknown_manufacturer_404(client):
    ac, _, _ = client
    res = await ac.get("/api/chargers/manufacturers/unknown-vendor")
    assert res.status_code == 404
