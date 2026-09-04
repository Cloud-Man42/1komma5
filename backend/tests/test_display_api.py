"""Display overview API tests."""

from __future__ import annotations

import pytest
from helpers import seed_recent_readings


async def _create_pi_device(
    ac,
    *,
    name: str = "Pi Display",
    device_type: str = "raspberry_pi",
    default_site_slug: str | None = "akarp",
) -> dict:
    response = await ac.post(
        "/api/apple-devices",
        json={
            "owner_label": "Henrik",
            "device_name": name,
            "device_type": device_type,
            "default_site_slug": default_site_slug,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["scopes"] == "display.read"
    return body


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_phone_device_gets_display_read_scope(client):
    ac, _, _ = client
    device = await _create_pi_device(ac, name="Henriks mobil", device_type="phone")
    assert device["device_type"] == "phone"
    assert device["scopes"] == "display.read"


@pytest.mark.asyncio
async def test_display_overview_requires_auth(client):
    ac, _, _ = client
    response = await ac.get("/api/v1/display/overview/akarp")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_display_overview_stream_requires_auth(client):
    ac, _, _ = client
    response = await ac.get("/api/v1/display/overview/akarp/stream")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_display_overview_sse_generator_emits_initial_payload(client):
    from unittest.mock import AsyncMock, patch

    from app.api.display import _display_overview_sse_generator
    from app.display_service import DisplayOverviewService

    ac, session_factory, settings = client
    await _create_pi_device(ac)
    await seed_recent_readings(
        session_factory,
        settings,
        "akarp",
        [(3200, 1780, 0, 1240, 58)],
    )

    request = AsyncMock()
    request.is_disconnected = AsyncMock(return_value=True)

    async with session_factory() as session:
        service = DisplayOverviewService(session, settings)
        with patch(
            "app.api.display.snapshot_pubsub_available",
            AsyncMock(return_value=False),
        ):
            chunks = [
                chunk
                async for chunk in _display_overview_sse_generator(
                    request,
                    session,
                    settings,
                    "akarp",
                    service,
                )
            ]

    assert len(chunks) == 1
    assert chunks[0].startswith("data: ")
    assert '"slug":"akarp"' in chunks[0] or '"slug": "akarp"' in chunks[0]


@pytest.mark.asyncio
async def test_display_overview_returns_payload(client):
    ac, session_factory, settings = client
    device = await _create_pi_device(ac)
    await seed_recent_readings(
        session_factory,
        settings,
        "akarp",
        [(3200, 1780, 0, 1240, 58)],
    )
    response = await ac.get(
        "/api/v1/display/overview/akarp",
        headers=_auth_headers(device["token"]),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["site"]["slug"] == "akarp"
    assert body["live"]["solar_power_kw"] == pytest.approx(3.2, abs=0.01)
    assert body["live"]["battery_soc_pct"] == pytest.approx(58, abs=0.1)
    assert "weather" in body
    assert "flow" in body
    assert body["flow"]["available"] is True


@pytest.mark.asyncio
async def test_display_overview_sections_expose_deadline_fields(client):
    """Vehicle/charger `ready_by` and spa `next_cleaning_at` must be present.

    They are null when no plan exists, which the kiosk renders as `--` rather
    than a fabricated timestamp.
    """
    ac, session_factory, settings = client
    device = await _create_pi_device(ac, name="Pi deadlines")
    await seed_recent_readings(session_factory, settings, "akarp", [(3200, 1780, 0, 1240, 58)])

    response = await ac.get(
        "/api/v1/display/overview/akarp",
        headers=_auth_headers(device["token"]),
    )
    assert response.status_code == 200
    body = response.json()
    assert "ready_by" in body["vehicle"]
    assert "ready_by" in body["charger"]
    assert "next_cleaning_at" in body["spa"]
    assert body["spa"]["next_cleaning_at"] is None


@pytest.mark.asyncio
async def test_display_overview_includes_phase2_fields(client):
    ac, session_factory, settings = client
    device = await _create_pi_device(ac, name="Pi phase2")
    await seed_recent_readings(session_factory, settings, "akarp", [(3200, 1780, 0, 1240, 58)])

    response = await ac.get(
        "/api/v1/display/overview/akarp",
        headers=_auth_headers(device["token"]),
    )
    assert response.status_code == 200
    body = response.json()
    assert "solar" in body
    assert "forecast_curve" in body["solar"]
    assert "lowest_ore_kwh" in body["price"]
    assert "highest_ore_kwh" in body["price"]
    assert "battery_charged_today_kwh" in body["live"]
    assert "battery_discharged_today_kwh" in body["live"]
    assert "decision_reason_sv" in body["charger"]
    assert "filter_cycles_completed_today" in body["spa"]
    assert "target_soc_pct" in body["vehicle"]


@pytest.mark.asyncio
async def test_next_spa_cleaning_at_returns_upcoming_window(client):
    """The display service reuses the flexible-load planner for spa cleaning."""
    import json
    from datetime import UTC, datetime, timedelta

    from app.display_service import _next_spa_cleaning_at
    from energy_core.db.models import FlexibleLoadPlanModel
    from energy_core.db.repositories import SiteRepository

    _, session_factory, _ = client
    now = datetime.now(UTC)
    past = now - timedelta(hours=5)
    upcoming = now + timedelta(hours=3)

    def window(start: datetime) -> dict:
        return {
            "start": start.isoformat(),
            "end": (start + timedelta(hours=2)).isoformat(),
            "duration_hours": 2.0,
            "expected_energy_kwh": 1.2,
            "expected_cost_sek": 1.5,
            "expected_energy_source": "SOLAR",
        }

    async with session_factory() as session:
        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None

        assert await _next_spa_cleaning_at(session, site.id) is None

        session.add(
            FlexibleLoadPlanModel(
                site_id=site.id,
                load_id="spa_cleaning",
                strategy="SOLAR_FIRST",
                window_start=past,
                window_end=past + timedelta(hours=2),
                windows_json=json.dumps([window(past), window(upcoming)]),
            )
        )
        await session.commit()

        resolved = await _next_spa_cleaning_at(session, site.id)

    assert resolved is not None
    assert abs((resolved - upcoming).total_seconds()) < 2


def test_change_pct_handles_missing_and_zero_baseline():
    from app.display_service import _change_pct

    assert _change_pct(138.0, 100.0) == 38.0
    assert _change_pct(79.0, 100.0) == -21.0
    # No baseline (first month of data) must not produce a fabricated delta.
    assert _change_pct(500.0, 0.0) is None
    # A negative baseline still compares by magnitude.
    assert _change_pct(-50.0, -100.0) == 50.0


def test_grid_direction_is_swedish_and_has_an_idle_deadband():
    from app.display_service import _GRID_DIRECTION_SV, _grid_direction

    assert _grid_direction(1.24, 0.0) == "export"
    assert _grid_direction(0.0, 0.9) == "import"
    # Below the deadband neither direction applies.
    assert _grid_direction(0.01, 0.01) == "idle"
    # Export wins when both are reported.
    assert _grid_direction(1.0, 1.0) == "export"

    assert _GRID_DIRECTION_SV["export"] == "Exporterar"
    assert _GRID_DIRECTION_SV["import"] == "Importerar"
    # Regression: the idle label used to leak the English word "Idle".
    assert _GRID_DIRECTION_SV["idle"] == "Balanserat"


def test_filter_status_sv_translates_arctic_spa_values():
    from energy_core.integrations.arctic_spa.operational_state import filter_status_sv

    assert filter_status_sv("Idle") == "Av"
    assert filter_status_sv("Filtering") == "Pågår"
    assert filter_status_sv("Sanitize") == "Rening"
    assert filter_status_sv(None) is None
    assert filter_status_sv("") is None
    # Unknown statuses pass through rather than being hidden.
    assert filter_status_sv("Cryogenic") == "Cryogenic"


@pytest.mark.asyncio
async def test_next_spa_cleaning_at_ignores_fully_past_plan(client):
    """A stale plan must yield None so the kiosk shows `--`, not a past time."""
    import json
    from datetime import UTC, datetime, timedelta

    from app.display_service import _next_spa_cleaning_at
    from energy_core.db.models import FlexibleLoadPlanModel
    from energy_core.db.repositories import SiteRepository

    _, session_factory, _ = client
    old = datetime.now(UTC) - timedelta(days=3)

    async with session_factory() as session:
        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        session.add(
            FlexibleLoadPlanModel(
                site_id=site.id,
                load_id="spa_cleaning",
                strategy="SOLAR_FIRST",
                window_start=old,
                window_end=old + timedelta(hours=2),
                windows_json=json.dumps(
                    [
                        {
                            "start": old.isoformat(),
                            "end": (old + timedelta(hours=2)).isoformat(),
                            "duration_hours": 2.0,
                            "expected_energy_kwh": 1.0,
                            "expected_cost_sek": 1.0,
                            "expected_energy_source": "SOLAR",
                        }
                    ]
                ),
            )
        )
        await session.commit()

        assert await _next_spa_cleaning_at(session, site.id) is None


@pytest.mark.asyncio
async def test_display_overview_unknown_site_returns_404(client):
    ac, _, _ = client
    device = await _create_pi_device(ac, name="Pi 2")
    response = await ac.get(
        "/api/v1/display/overview/missing",
        headers=_auth_headers(device["token"]),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_display_forbidden_without_scope(client):
    ac, session_factory, _ = client
    from energy_core.auth.device_tokens import generate_device_token
    from energy_core.db.apple_device_repo import AppleDeviceRepository

    async with session_factory() as session:
        repo = AppleDeviceRepository(session)
        generated = generate_device_token()
        await repo.create(
            owner_label="Test",
            device_name="Widget only",
            device_type="iphone",
            generated=generated,
            scopes="widget.read",
        )
        await session.commit()
        token = generated.token

    response = await ac.get(
        "/api/v1/display/overview/akarp",
        headers=_auth_headers(token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_display_revoked_token_returns_401(client):
    ac, _, _ = client
    device = await _create_pi_device(ac, name="Pi revoked")
    revoke = await ac.post(f"/api/apple-devices/{device['id']}/revoke")
    assert revoke.status_code == 200
    response = await ac.get(
        "/api/v1/display/overview/akarp",
        headers=_auth_headers(device["token"]),
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_display_overview_serves_any_site_and_flags_dead_data(client):
    """A second house works on slug alone, but must not pass off old data as live.

    The Danish site had no Heartbeat mapping, so its newest reading was over two
    weeks old while the API answered 200. The payload has to say so.
    """
    from datetime import UTC, datetime, timedelta

    from energy_core.db.repositories import EnergyReadingRepository, SiteRepository
    from energy_core.domain import NormalizedEnergyReading

    ac, session_factory, settings = client
    device = await _create_pi_device(
        ac,
        name="Pi Danmark",
        default_site_slug="summer-house-denmark",
    )

    stale_at = datetime.now(UTC) - timedelta(days=16)
    async with session_factory() as session:
        site = await SiteRepository(session).get_by_slug("summer-house-denmark")
        assert site is not None
        await EnergyReadingRepository(session, is_sqlite=settings.is_sqlite).upsert_reading(
            site.id,
            NormalizedEnergyReading(
                site_slug="summer-house-denmark",
                recorded_at=stale_at,
                solar_production_w=2975.0,
                consumption_w=486.0,
                grid_import_w=0.0,
                grid_export_w=2529.0,
                battery_soc_pct=74.0,
                battery_power_w=724.0,
            ),
        )
        await session.commit()

    response = await ac.get(
        "/api/v1/display/overview/summer-house-denmark",
        headers=_auth_headers(device["token"]),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["site"]["slug"] == "summer-house-denmark"
    assert body["site"]["timezone"] == "Europe/Copenhagen"
    assert body["freshness"]["stale"] is True
    assert body["freshness"]["connection_state"] == "STALE"
    assert body["freshness"]["data_age_seconds"] > 14 * 24 * 3600


# --- Browser enrollment (tablets and anything else without the Pi's proxy) ---


@pytest.mark.asyncio
async def test_tablet_device_type_gets_the_display_scope(client):
    """A tablet runs the same full-screen dashboard, so it needs `display.read`."""
    ac, _, _ = client
    device = await _create_pi_device(ac, name="Surfplatta", device_type="tablet")
    response = await ac.get(
        "/api/v1/display/overview/akarp",
        headers=_auth_headers(device["token"]),
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_enroll_sets_an_httponly_cookie_and_hides_the_token(client):
    ac, _, _ = client
    device = await _create_pi_device(ac, name="Surfplatta", device_type="tablet")

    response = await ac.get(f"/api/v1/display/enroll?token={device['token']}")

    assert response.status_code == 303
    assert response.headers["location"] == "/display/akarp"
    cookie = response.headers["set-cookie"]
    assert "emic_display_token=" in cookie
    assert "httponly" in cookie.lower()
    assert "samesite=lax" in cookie.lower()
    # The token must not survive in the address bar or history.
    assert device["token"] not in response.headers["location"]


@pytest.mark.asyncio
async def test_enrolled_browser_reads_the_overview_with_only_the_cookie(client):
    ac, _, _ = client
    device = await _create_pi_device(ac, name="Surfplatta", device_type="tablet")
    enroll = await ac.get(f"/api/v1/display/enroll?token={device['token']}")
    assert enroll.status_code == 303

    # No Authorization header: the cookie stored by the client jar is the only proof.
    response = await ac.get("/api/v1/display/overview/akarp")

    assert response.status_code == 200
    assert response.json()["site"]["slug"] == "akarp"


@pytest.mark.asyncio
async def test_overview_rejects_an_unknown_cookie(client):
    ac, _, _ = client
    ac.cookies.set("emic_display_token", "emic_dev_notarealtoken")
    response = await ac.get("/api/v1/display/overview/akarp")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_overview_rejects_a_revoked_cookie(client):
    """Revoking the device must lock the tablet out, not just the Pi."""
    ac, _, _ = client
    device = await _create_pi_device(ac, name="Surfplatta", device_type="tablet")
    enroll = await ac.get(f"/api/v1/display/enroll?token={device['token']}")
    assert enroll.status_code == 303
    assert (await ac.get("/api/v1/display/overview/akarp")).status_code == 200

    revoke = await ac.post(f"/api/apple-devices/{device['id']}/revoke")
    assert revoke.status_code == 200

    assert (await ac.get("/api/v1/display/overview/akarp")).status_code == 401


@pytest.mark.asyncio
async def test_a_bearer_header_takes_precedence_over_a_stale_cookie(client):
    """The Pi's proxy always injects a header; a leftover cookie must not break it."""
    ac, _, _ = client
    device = await _create_pi_device(ac, name="Pi with cookie")
    ac.cookies.set("emic_display_token", "emic_dev_stalecookie")

    response = await ac.get(
        "/api/v1/display/overview/akarp",
        headers=_auth_headers(device["token"]),
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_enroll_rejects_an_unknown_token_without_setting_a_cookie(client):
    ac, _, _ = client
    response = await ac.get("/api/v1/display/enroll?token=emic_dev_notarealtoken")
    assert response.status_code == 401
    assert "set-cookie" not in response.headers


@pytest.mark.asyncio
async def test_enroll_rejects_a_token_without_the_display_scope(client):
    """A widget token must not be upgradable into a display cookie."""
    ac, session_factory, _ = client
    from energy_core.auth.device_tokens import generate_device_token
    from energy_core.db.apple_device_repo import AppleDeviceRepository

    async with session_factory() as session:
        generated = generate_device_token()
        await AppleDeviceRepository(session).create(
            owner_label="Test",
            device_name="Phone",
            device_type="iphone",
            generated=generated,
            scopes="widget.read",
        )
        await session.commit()

    response = await ac.get(f"/api/v1/display/enroll?token={generated.token}")

    assert response.status_code == 403
    assert "set-cookie" not in response.headers


@pytest.mark.asyncio
async def test_enroll_requires_a_slug_when_the_device_has_no_default_site(client):
    ac, _, _ = client
    device = await _create_pi_device(
        ac,
        name="Surfplatta",
        device_type="tablet",
        default_site_slug=None,
    )

    response = await ac.get(f"/api/v1/display/enroll?token={device['token']}")

    assert response.status_code == 400
    assert "set-cookie" not in response.headers


@pytest.mark.asyncio
async def test_enroll_refuses_a_slug_that_would_redirect_off_the_dashboard(client):
    """The slug lands in a Location header, so it may not carry a path or host."""
    ac, _, _ = client
    device = await _create_pi_device(ac, name="Surfplatta", device_type="tablet")

    for hostile in ("../evil", "//evil.example.com", "akarp?x=1"):
        response = await ac.get(
            "/api/v1/display/enroll",
            params={"token": device["token"], "slug": hostile},
        )
        assert response.status_code == 400, hostile
        assert "set-cookie" not in response.headers


@pytest.mark.asyncio
async def test_enroll_honours_an_explicit_slug(client):
    ac, _, _ = client
    device = await _create_pi_device(ac, name="Surfplatta", device_type="tablet")

    response = await ac.get(
        "/api/v1/display/enroll",
        params={"token": device["token"], "slug": "AKARP"},
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/display/akarp"


@pytest.mark.asyncio
async def test_enroll_cookie_is_not_secure_over_plain_http(client):
    """The LAN deployment serves HTTP; a Secure cookie would be dropped there."""
    ac, _, _ = client
    device = await _create_pi_device(ac, name="Surfplatta", device_type="tablet")

    response = await ac.get(f"http://test/api/v1/display/enroll?token={device['token']}")

    assert response.status_code == 303
    assert "Secure" not in response.headers["set-cookie"]


@pytest.mark.asyncio
async def test_enroll_cookie_is_secure_over_https(client):
    ac, _, _ = client
    device = await _create_pi_device(ac, name="Surfplatta", device_type="tablet")

    response = await ac.get(f"https://test/api/v1/display/enroll?token={device['token']}")

    assert response.status_code == 303
    assert "Secure" in response.headers["set-cookie"]


@pytest.mark.asyncio
async def test_enroll_cookie_is_secure_with_forwarded_proto(client):
    """Caddy terminates TLS and forwards X-Forwarded-Proto to the backend."""
    ac, _, _ = client
    device = await _create_pi_device(ac, name="Surfplatta", device_type="tablet")

    response = await ac.get(
        f"http://test/api/v1/display/enroll?token={device['token']}",
        headers={"X-Forwarded-Proto": "https", "X-Forwarded-For": "203.0.113.10"},
    )

    assert response.status_code == 303
    assert "Secure" in response.headers["set-cookie"]
