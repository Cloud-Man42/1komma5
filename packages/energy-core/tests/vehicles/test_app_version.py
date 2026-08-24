"""Mercedes app version and token session tests."""

from __future__ import annotations

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


def test_websocket_headers_include_locale_and_session():
    manager = MercedesAppVersionManager("Europe")
    headers = manager.websocket_headers("ABCD-1234", "token-value")
    assert headers["APP-SESSION-ID"] == "ABCD-1234"
    assert headers["X-SessionId"] == "ABCD-1234"
    assert headers["Authorization"] == "token-value"
    assert headers["X-Locale"] == "de-DE"
    assert headers["OUTPUT-FORMAT"] == "PROTO"
