import pytest
from energy_core.db.heartbeat_settings_repo import (
    HeartbeatSettingsRecord,
)
from energy_core.heartbeat_config import build_heartbeat_connection_info
from energy_core.heartbeat_connection import (
    HeartbeatConnectionType,
    build_heartbeat_api_url,
    connection_type_label,
)
from energy_core.providers.onekommafive import HeartbeatRuntimeConfig, OneKommaFiveHeartbeatProvider


def _record(**kwargs) -> HeartbeatSettingsRecord:
    defaults = {
        "connection_type": "mock",
        "host": "",
        "port": 443,
        "use_tls": True,
        "api_path": "/api",
        "poll_interval_seconds": 60,
        "dashboard_refresh_seconds": 30,
        "username": "",
        "password_configured": False,
        "api_token_configured": False,
        "api_url": None,
        "updated_at": None,
    }
    defaults.update(kwargs)
    return HeartbeatSettingsRecord(**defaults)


def test_build_heartbeat_api_url_cloud():
    url = build_heartbeat_api_url(HeartbeatConnectionType.CLOUD)
    assert url == "https://heartbeat.1komma5grad.com/api"


def test_build_heartbeat_api_url_local():
    url = build_heartbeat_api_url(
        HeartbeatConnectionType.LOCAL,
        host="192.168.1.50",
        port=8080,
        use_tls=False,
    )
    assert url == "http://192.168.1.50:8080/api"


def test_build_heartbeat_api_url_local_https_default_port():
    url = build_heartbeat_api_url(
        HeartbeatConnectionType.LOCAL,
        host="192.168.1.50",
        port=443,
        use_tls=True,
    )
    assert url == "https://192.168.1.50/api"


def test_heartbeat_connection_info_mock():
    info = build_heartbeat_connection_info(_record(), [])
    assert info.implementation_status == "mock"
    assert info.api_url is None


def test_heartbeat_connection_info_cloud_not_configured():
    info = build_heartbeat_connection_info(
        _record(
            connection_type="cloud",
            host="heartbeat.1komma5grad.com",
            api_url="https://heartbeat.1komma5grad.com/api",
        ),
        [],
    )
    assert info.implementation_status == "not_configured"


def test_heartbeat_connection_info_local_configured():
    info = build_heartbeat_connection_info(
        _record(
            connection_type="local",
            host="192.168.1.10",
            port=8080,
            use_tls=False,
            api_url="http://192.168.1.10:8080/api",
        ),
        [],
    )
    assert info.implementation_status == "configured"
    assert info.api_url == "http://192.168.1.10:8080/api"


@pytest.mark.asyncio
async def test_onekommafive_provider_returns_empty_without_credentials():
    provider = OneKommaFiveHeartbeatProvider(
        HeartbeatRuntimeConfig(
            connection_type="cloud",
            api_url="https://heartbeat.1komma5grad.com/api",
            username="",
            password="",
            api_token="",
            site_system_ids={"akarp": "00000000-0000-0000-0000-000000000001"},
        )
    )
    readings = await provider.fetch_readings()
    assert readings == []


def test_connection_type_label():
    assert connection_type_label("local") == "Lokal gateway (IP/port)"
