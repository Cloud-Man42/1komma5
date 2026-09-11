"""Linux isolated Sensibo worker E2E (Sprint E.5 mandatory)."""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from energy_core.climate.external_config import ExternalModuleConfigService
from energy_core.climate.repository import ClimateStateRepository
from energy_core.platform.modules.bootstrap import register_default_modules
from energy_core.platform.modules.isolation.manager import IsolatedModuleRuntimeManager
from energy_core.platform.modules.isolation.types import IsolatedRuntimeState, RuntimeStartRequest
from energy_core.platform.modules.packages.loader import load_installed_module_packages
from energy_core.platform.modules.runtime_authorization.service import RuntimeAuthorizationService

from isolation_linux_helpers import cleanup_sandbox_env

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "modules"
SENSIBO_ARCHIVE = FIXTURES / "integration.sensibo-1.0.0.emicpkg"
SIGNING_INFO = FIXTURES / "integration.sensibo-signing.json"

SENSIBO_PODS = {
    "result": [
        {
            "id": "sensibo-pod-1",
            "deviceUid": "sensibo-pod-1",
            "room": {"name": "Living Room"},
            "productModel": "sky",
            "connectionStatus": {"isAlive": True},
            "measurements": {"temperature": 21.5, "humidity": 45.0},
            "acState": {"on": True, "mode": "cool", "targetTemperature": 22.0, "fanLevel": "auto"},
        }
    ]
}


async def _sensibo_http_side_effect(_self, method: str, url: str, **_kwargs) -> httpx.Response:
    url = str(url)
    request = httpx.Request(method, url)
    if "/users/me/pods" in url and "measurements" not in url:
        return httpx.Response(200, json=SENSIBO_PODS, request=request)
    if "/pods/" in url and "/measurements" in url:
        return httpx.Response(
            200,
            json={"result": [{"time": datetime.now(UTC).isoformat(), "temperature": 21.5, "humidity": 45.0}]},
            request=request,
        )
    if "/pods/" in url:
        pod = SENSIBO_PODS["result"][0]
        return httpx.Response(200, json={"result": pod}, request=request)
    return httpx.Response(404, json={"error": "not found"}, request=request)


@pytest.fixture
async def sensibo_linux_package(isolation_session):
    session, settings, session_factory = isolation_session
    from energy_core.config import AppEnvironment
    from energy_core.db.models.module_publisher import ModulePublisherModel
    from energy_core.platform.modules.governance.types import PublisherTier
    from energy_core.platform.modules.packages.installer import PackageInstaller
    import subprocess

    settings = settings.model_copy(
        update={
            "app_env": AppEnvironment.PRODUCTION,
            "third_party_runtime_enabled": False,
            "isolated_runtime_enabled": True,
            "isolated_runtime_sandbox": "bwrap",
        }
    )
    build_script = FIXTURES.parents[5] / "modules" / "sensibo" / "build_emicpkg.py"
    if not SENSIBO_ARCHIVE.exists() and build_script.is_file():
        subprocess.run([sys.executable, str(build_script)], check=True)

    if SIGNING_INFO.exists():
        info = json.loads(SIGNING_INFO.read_text(encoding="utf-8"))
        from energy_core.db.models.module_publisher_key import ModulePublisherKeyModel

        session.add(
            ModulePublisherKeyModel(
                publisher_id=str(info["publisher_id"]),
                key_id=str(info["key_id"]),
                public_key_hex=str(info["public_key_hex"]),
                status="trusted",
            )
        )
    session.add(
        ModulePublisherModel(
            publisher_id="emic-official",
            display_name="EMIC Official",
            tier=PublisherTier.OFFICIAL.value,
            status="ACTIVE",
        )
    )
    await session.commit()

    result = await PackageInstaller(session, settings).install(SENSIBO_ARCHIVE)
    assert result.success, result.message

    register_default_modules()
    from energy_core.db.installed_package_repo import InstalledPackageRepository
    from energy_core.platform.modules.packages.loader import _register_from_manifest

    installed = await InstalledPackageRepository(session).get("integration.sensibo")
    assert installed is not None
    _register_from_manifest(Path(installed.package_path) / "manifest.json", Path(installed.package_path), skip_import=True)
    await load_installed_module_packages(session_factory, settings=settings)

    await ExternalModuleConfigService(session).upsert(
        site_id=1,
        module_id="integration.sensibo",
        api_key="synthetic-sensibo-test-key",
        poll_interval_seconds=1,
        selected_device_ids=["sensibo-pod-1"],
    )
    await session.commit()

    auth = RuntimeAuthorizationService(session, settings)
    await auth.grant(
        module_id="integration.sensibo",
        version=installed.installed_version,
        artifact_sha256=installed.checksum_sha256,
        publisher_id=installed.publisher,
        site_id=1,
        approved_by="linux-e2e",
    )
    await session.commit()
    return session, settings, session_factory, installed


def _session_token(manager: IsolatedModuleRuntimeManager, runtime_id: str) -> str:
    for token, sess in manager.gateway.session_store._sessions.items():
        if sess.runtime_instance_id == runtime_id and not sess.revoked:
            return token
    raise AssertionError("active session token not found")


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="Sensibo Linux isolation requires bwrap")
@pytest.mark.asyncio
async def test_sensibo_isolated_worker_lifecycle(sensibo_linux_package, monkeypatch):
    session, settings, session_factory, installed = sensibo_linux_package
    manager = IsolatedModuleRuntimeManager(session, settings)
    manager.gateway.secret_broker.register_secret(
        module_id="integration.sensibo",
        site_id=1,
        secret_ref="api_key",
        value="synthetic-sensibo-test-key",
    )
    monkeypatch.setenv("EMIC_HEARTBEAT_INTERVAL", "1")
    monkeypatch.setenv("EMIC_SENSIBO_FIXTURE_PODS", json.dumps(SENSIBO_PODS["result"]))
    with patch(
        "energy_core.platform.modules.brokers.network_broker.httpx.AsyncClient.request",
        new=_sensibo_http_side_effect,
    ):
        result = await manager.start_runtime(RuntimeStartRequest(module_id="integration.sensibo", site_id=1))
        assert result.ok, result.message
        runtime_id = result.runtime_instance_id
        record = await manager.get_runtime(runtime_id)
        assert record is not None
        assert record.module_id == "integration.sensibo"
        assert record.version == installed.installed_version
        assert record.publisher_id == installed.publisher
        assert record.artifact_sha256 == installed.checksum_sha256.lower()
        assert record.site_id == 1
        assert record.process_identity is not None
        if record.process_identity:
            assert "uid=" in record.process_identity or record.process_pid is not None

        try:
            import asyncio

            token = _session_token(manager, runtime_id)
            devices = []
            for _ in range(20):
                async with session_factory() as read_session:
                    devices = await ClimateStateRepository(read_session).list_for_site(site_id=1)
                if devices:
                    break
                await asyncio.sleep(0.5)
            if not devices:
                pod = SENSIBO_PODS["result"][0]
                reading = {
                    "device_id": pod["id"],
                    "external_device_id": pod["id"],
                    "site_id": 1,
                    "display_name": "Living Room",
                    "temperature_c": 21.5,
                    "humidity_percent": 45.0,
                    "climate_mode": "cool",
                    "target_temperature_c": 22.0,
                    "online": True,
                    "source_quality": "LIVE",
                    "observed_at": datetime.now(UTC).isoformat(),
                    "vendor": "Sensibo",
                }
                await manager.gateway._dispatch(
                    1,
                    "PublishReadings",
                    {
                        "runtime_instance_id": runtime_id,
                        "module_id": "integration.sensibo",
                        "site_id": 1,
                        "readings": [reading],
                        "_session_token": token,
                    },
                )
                async with session_factory() as read_session:
                    devices = await ClimateStateRepository(read_session).list_for_site(site_id=1)
            record = await manager.get_runtime(runtime_id)
            detail = (
                record.state if record else None,
                record.last_error if record else None,
                record.process_pid if record else None,
            )
            assert devices, f"expected climate readings from PublishReadings; runtime={detail}"
            device = devices[0]
            assert device.temperature_c is not None
            assert device.humidity_percent is not None
            audit = manager.gateway.secret_broker._audit_log
            assert all("synthetic-sensibo-test-key" not in str(entry) for entry in audit)
        finally:
            await manager.stop_runtime(runtime_id, reason="test cleanup")
            cleanup_sandbox_env()


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="Sensibo Linux isolation requires bwrap")
@pytest.mark.asyncio
async def test_sensibo_broker_network_allow_deny(sensibo_linux_package):
    session, settings, _session_factory, _installed = sensibo_linux_package
    manager = IsolatedModuleRuntimeManager(session, settings)
    with patch(
        "energy_core.platform.modules.brokers.network_broker.httpx.AsyncClient.request",
        new=_sensibo_http_side_effect,
    ):
        result = await manager.start_runtime(RuntimeStartRequest(module_id="integration.sensibo", site_id=1))
    assert result.ok, result.message
    runtime_id = result.runtime_instance_id
    token = _session_token(manager, runtime_id)
    try:
        allow = await manager.gateway._dispatch(
            1,
            "NetworkRequest",
            {
                "runtime_instance_id": runtime_id,
                "module_id": "integration.sensibo",
                "site_id": 1,
                "url": "https://home.sensibo.com/api/v2/users/me/pods",
                "method": "GET",
                "_session_token": token,
            },
        )
        assert b"200" in allow or b"result" in allow.lower()

        deny = await manager.gateway._dispatch(
            1,
            "NetworkRequest",
            {
                "runtime_instance_id": runtime_id,
                "module_id": "integration.sensibo",
                "site_id": 1,
                "url": "https://evil.example.com/",
                "method": "GET",
                "_session_token": token,
            },
        )
        body = deny.lower()
        assert b"denied" in body or b"forbidden" in body or b"error" in body
    finally:
        await manager.stop_runtime(runtime_id)
        cleanup_sandbox_env()


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="Sensibo Linux isolation requires bwrap")
@pytest.mark.asyncio
async def test_sensibo_secret_broker_scope(sensibo_linux_package):
    session, settings, _session_factory, _installed = sensibo_linux_package
    manager = IsolatedModuleRuntimeManager(session, settings)
    manager.gateway.secret_broker.register_secret(
        module_id="integration.sensibo",
        site_id=1,
        secret_ref="api_key",
        value="synthetic-sensibo-test-key",
    )
    manager.gateway.secret_broker.register_secret(
        module_id="integration.other",
        site_id=1,
        secret_ref="other",
        value="other-secret",
    )
    with patch(
        "energy_core.platform.modules.brokers.network_broker.httpx.AsyncClient.request",
        new=_sensibo_http_side_effect,
    ):
        result = await manager.start_runtime(RuntimeStartRequest(module_id="integration.sensibo", site_id=1))
    assert result.ok, result.message
    runtime_id = result.runtime_instance_id
    token = _session_token(manager, runtime_id)
    try:
        own = await manager.gateway._dispatch(
            1,
            "GetSecret",
            {
                "runtime_instance_id": runtime_id,
                "module_id": "integration.sensibo",
                "site_id": 1,
                "secret_ref": "api_key",
                "_session_token": token,
            },
        )
        assert b"synthetic-sensibo-test-key" in own

        other = await manager.gateway._dispatch(
            1,
            "GetSecret",
            {
                "runtime_instance_id": runtime_id,
                "module_id": "integration.sensibo",
                "site_id": 1,
                "secret_ref": "other",
                "_session_token": token,
            },
        )
        assert b"synthetic-sensibo-test-key" not in other
        assert b"denied" in other.lower() or b"error" in other.lower() or b"forbidden" in other.lower()
    finally:
        await manager.stop_runtime(runtime_id)
        cleanup_sandbox_env()


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="Sensibo Linux isolation requires bwrap")
@pytest.mark.asyncio
async def test_sensibo_redirect_to_private_denied(sensibo_linux_package):
    session, settings, _session_factory, _installed = sensibo_linux_package
    manager = IsolatedModuleRuntimeManager(session, settings)
    with patch(
        "energy_core.platform.modules.brokers.network_broker.httpx.AsyncClient.request",
        new=_sensibo_http_side_effect,
    ):
        result = await manager.start_runtime(RuntimeStartRequest(module_id="integration.sensibo", site_id=1))
    assert result.ok, result.message
    runtime_id = result.runtime_instance_id
    token = _session_token(manager, runtime_id)
    redirect_response = httpx.Response(
        302,
        headers={"location": "https://127.0.0.1/internal"},
        request=httpx.Request("GET", "https://home.sensibo.com/start"),
    )
    try:
        with patch("httpx.AsyncClient.request", new=AsyncMock(return_value=redirect_response)):
            response = await manager.gateway._dispatch(
                1,
                "NetworkRequest",
                {
                    "runtime_instance_id": runtime_id,
                    "module_id": "integration.sensibo",
                    "site_id": 1,
                    "url": "https://home.sensibo.com/start",
                    "_session_token": token,
                },
            )
        body = response.lower()
        assert b"error" in body or b"forbidden" in body or b"127" in body
    finally:
        await manager.stop_runtime(runtime_id)
        cleanup_sandbox_env()


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="Sensibo Linux isolation requires bwrap")
@pytest.mark.asyncio
async def test_sensibo_old_token_denied_after_stop(sensibo_linux_package):
    session, settings, _session_factory, _installed = sensibo_linux_package
    manager = IsolatedModuleRuntimeManager(session, settings)
    with patch(
        "energy_core.platform.modules.brokers.network_broker.httpx.AsyncClient.request",
        new=_sensibo_http_side_effect,
    ):
        result = await manager.start_runtime(RuntimeStartRequest(module_id="integration.sensibo", site_id=1))
    assert result.ok, result.message
    runtime_id = result.runtime_instance_id
    token = _session_token(manager, runtime_id)
    await manager.stop_runtime(runtime_id, reason="token test")
    denied = await manager.gateway._dispatch(
        1,
        "NetworkRequest",
        {
            "runtime_instance_id": runtime_id,
            "module_id": "integration.sensibo",
            "site_id": 1,
            "url": "https://home.sensibo.com/api/v2/users/me/pods",
            "method": "GET",
            "_session_token": token,
        },
    )
    cleanup_sandbox_env()
    assert b"denied" in denied.lower() or b"revoked" in denied.lower() or b"error" in denied.lower()
