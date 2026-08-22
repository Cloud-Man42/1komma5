import pytest

from helpers import create_charger


@pytest.mark.asyncio
async def test_site_energy_config_defaults(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/akarp/energy-config")
    assert res.status_code == 200
    body = res.json()
    assert body["site_slug"] == "akarp"
    assert body["load_includes_ev_charger"] is None
    assert body["inverter_display_name"] == "Sungrow Hybrid Inverter SH10"


@pytest.mark.asyncio
async def test_site_energy_config_update_load_includes_ev(client):
    ac, _, _ = client
    res = await ac.put(
        "/api/sites/akarp/energy-config",
        json={"load_includes_ev_charger": True},
    )
    assert res.status_code == 200
    assert res.json()["load_includes_ev_charger"] is True

    clear = await ac.put(
        "/api/sites/akarp/energy-config",
        json={"clear_load_includes_ev_charger": True},
    )
    assert clear.status_code == 200
    assert clear.json()["load_includes_ev_charger"] is None


@pytest.mark.asyncio
async def test_bridge_status_fuse_headroom_with_site_fuse(client):
    ac, session_factory, _ = client
    async with session_factory() as session:
        from energy_core.db.repositories import SiteRepository

        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        site.main_fuse_a = 25.0
        site.safety_margin_a = 2.0
        await session.commit()

    charger = await create_charger(ac, "akarp", name="Fuse Test")
    charger_id = charger["id"]

    res = await ac.get(f"/api/sites/akarp/ev-chargers/{charger_id}/bridge-status")
    assert res.status_code == 200
    assert res.json()["fuse_headroom_a"] == 23.0

    await ac.delete(f"/api/sites/akarp/ev-chargers/{charger_id}")
