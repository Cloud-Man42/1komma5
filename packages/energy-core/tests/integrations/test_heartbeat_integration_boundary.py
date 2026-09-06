"""Tests for Heartbeat integration boundary modules."""

from __future__ import annotations


def test_heartbeat_client_factory_facade():
    from energy_core.heartbeat_client_factory import create_heartbeat_client as shim
    from energy_core.integrations.heartbeat.client_factory import create_heartbeat_client as direct

    assert shim is direct


def test_heartbeat_legacy_shims_reexport_integration():
    from energy_core import heartbeat_auth as auth_shim
    from energy_core import heartbeat_client as client_shim
    from energy_core import heartbeat_connection as connection_shim
    from energy_core.integrations.heartbeat import auth, client, connection

    assert auth_shim.fetch_bearer_token is auth.fetch_bearer_token
    assert client_shim.HeartbeatClient is client.HeartbeatClient
    assert connection_shim.CLOUD_HOST is connection.CLOUD_HOST


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
