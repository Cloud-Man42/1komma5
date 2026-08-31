"""Mercedes app version and token session tests."""

from __future__ import annotations

import httpx
import pytest

from energy_core.vehicles.mercedes.auth.app_version import MercedesAppVersionManager
from energy_core.vehicles.mercedes.auth.token_store import MercedesTokenBundle, MercedesTokenStore
from energy_core.vehicles.mercedes.auth.login import MercedesLoginFlow


def test_app_version_updates_from_force_update_config():
    manager = MercedesAppVersionManager("Europe")
    updated = manager.apply_config(
        {
            "forceUpdate": {
                "status": "FORCE",
                "applicationVersion": "1.70.0 (3100)",
            }
        }
    )
    assert updated is True
    assert manager.application_version == "1.70.0 (3100)"


def test_app_version_ignores_ok_status():
    manager = MercedesAppVersionManager("Europe")
    original = manager.application_version
    updated = manager.apply_config({"forceUpdate": {"status": "OK", "applicationVersion": "9.9.9"}})
    assert updated is False
    assert manager.application_version == original


def test_token_store_generates_missing_session_id():
    flow = MercedesLoginFlow(region="Europe", device_guid="device-123")
    store = MercedesTokenStore(login_flow=flow)
    bundle = MercedesTokenBundle(
        access_token="access",
        refresh_token="refresh",
        expires_at=9_999_999_999,
        device_guid="device-123",
        session_id="",
    )
    store.load(bundle)
    assert store.session_id
    assert len(store.session_id) >= 32


@pytest.mark.asyncio
async def test_refresh_rejects_a_client_passed_instead_of_a_loader():
    """Passing the AsyncClient here silently broke token refresh for a week."""
    manager = MercedesAppVersionManager("Europe")
    async with httpx.AsyncClient() as client:
        with pytest.raises(TypeError, match="config_loader must be callable, got AsyncClient"):
            await manager.refresh(client, force=True)


@pytest.mark.asyncio
async def test_refresh_applies_the_version_from_the_loader():
    manager = MercedesAppVersionManager("Europe")

    async def loader():
        return {"forceUpdate": {"status": "FORCE", "applicationVersion": "1.99.0 (4200)"}}

    assert await manager.refresh(loader, force=True) is True
    assert manager.application_version == "1.99.0 (4200)"


@pytest.mark.asyncio
async def test_refresh_skips_the_loader_when_the_version_is_fresh():
    manager = MercedesAppVersionManager("Europe")
    calls = 0

    async def loader():
        nonlocal calls
        calls += 1
        return {"applicationVersion": "1.99.0 (4200)"}

    await manager.refresh(loader, force=True)
    await manager.refresh(loader)

    assert calls == 1


@pytest.mark.asyncio
async def test_refresh_ignores_a_non_dict_config():
    manager = MercedesAppVersionManager("Europe")
    original = manager.application_version

    async def loader():
        return "not a config"

    assert await manager.refresh(loader, force=True) is False
    assert manager.application_version == original


def test_webapi_headers_never_repeat_a_header_name():
    """Duplicates made the widget API answer 400, so no name may appear twice."""
    manager = MercedesAppVersionManager("Europe")
    headers = manager.webapi_headers("ABCD-1234")
    lowered = [name.lower() for name in headers]
    assert sorted(lowered) == sorted(set(lowered))


def test_webapi_headers_keep_the_webapi_spelling_and_values():
    manager = MercedesAppVersionManager("Europe")
    headers = manager.webapi_headers("ABCD-1234")
    assert headers["X-SessionId"] == "ABCD-1234"
    assert headers["X-ApplicationName"] == "mycar-store-ece"
    assert headers["ris-application-version"] == manager.application_version
    assert "X-Applicationname" not in headers
    assert "Ris-Application-Version" not in headers


def test_webapi_headers_survive_an_httpx_round_trip_without_duplicates():
    manager = MercedesAppVersionManager("Europe")
    request = httpx.Request(
        "GET",
        "https://widget.emea-prod.mobilesdk.mercedes-benz.com/v1/vehicle/VIN/vehicleattributes",
        headers=manager.webapi_headers("ABCD-1234"),
    )
    assert len(request.headers.get_list("X-ApplicationName")) == 1
    assert len(request.headers.get_list("ris-application-version")) == 1
    assert len(request.headers.get_list("X-SessionId")) == 1


def test_vehicle_attributes_request_includes_proto_output_format():
    manager = MercedesAppVersionManager("Europe")
    headers = manager.webapi_headers("ABCD-1234")
    headers["Authorization"] = "Bearer token"
    headers["OUTPUT-FORMAT"] = "PROTO"
    request = httpx.Request(
        "GET",
        "https://widget.emea-prod.mobilesdk.mercedes-benz.com/v1/vehicle/VIN/vehicleattributes",
        headers=headers,
    )
    assert request.headers["OUTPUT-FORMAT"] == "PROTO"


def test_webapi_headers_track_a_version_update():
    manager = MercedesAppVersionManager("Europe")
    manager.apply_config({"forceUpdate": {"status": "FORCE", "applicationVersion": "1.80.0 (3200)"}})
    headers = manager.webapi_headers("ABCD-1234")
    assert headers["ris-application-version"] == "1.80.0 (3200)"


def test_websocket_headers_include_locale_and_session():
    manager = MercedesAppVersionManager("Europe")
    headers = manager.websocket_headers("ABCD-1234", "token-value")
    assert headers["APP-SESSION-ID"] == "ABCD-1234"
    assert headers["X-SessionId"] == "ABCD-1234"
    assert headers["Authorization"] == "token-value"
    assert headers["X-Locale"] == "de-DE"
    assert headers["OUTPUT-FORMAT"] == "PROTO"
