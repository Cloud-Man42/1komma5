"""Tests for Heartbeat integration boundary modules."""

from __future__ import annotations

from pathlib import Path


def test_heartbeat_integration_modules_are_canonical() -> None:
    from energy_core.integrations.heartbeat import auth, client, connection
    from energy_core.integrations.heartbeat.client_factory import create_heartbeat_client

    assert callable(auth.fetch_bearer_token)
    assert client.HeartbeatClient is not None
    assert connection.CLOUD_HOST
    assert callable(create_heartbeat_client)


def test_legacy_heartbeat_shim_modules_removed() -> None:
    repo = Path(__file__).resolve().parents[4]
    legacy = [
        "packages/energy-core/src/energy_core/heartbeat_auth.py",
        "packages/energy-core/src/energy_core/heartbeat_config.py",
        "packages/energy-core/src/energy_core/heartbeat_connection.py",
        "packages/energy-core/src/energy_core/heartbeat_client_factory.py",
        "packages/energy-core/src/energy_core/heartbeat_client.py",
    ]
    for rel in legacy:
        assert not (repo / rel).exists(), rel


def test_collector_imports_heartbeat_integration_not_vendor_package():
    import ast
    from pathlib import Path

    source = Path(__file__).resolve().parents[4] / "collector" / "app" / "collector.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert "energy_core.heartbeat.bridge.decision_engine" not in modules
    assert "energy_core.integrations.heartbeat.client_factory" in modules
