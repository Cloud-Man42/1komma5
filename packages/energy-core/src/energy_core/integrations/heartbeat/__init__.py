"""HeartBeat integration package."""

__all__ = [
    "CLOUD_PORT",
    "HeartbeatAuthError",
    "HeartbeatConnectionInfo",
    "HeartbeatConnectionType",
    "build_heartbeat_connection_info",
    "create_heartbeat_client",
    "parse_live_overview",
]


def __getattr__(name: str):
    if name == "HeartbeatAuthError":
        from energy_core.integrations.heartbeat.auth import HeartbeatAuthError

        return HeartbeatAuthError
    if name in {"HeartbeatConnectionInfo", "build_heartbeat_connection_info"}:
        from energy_core.integrations.heartbeat import config

        return getattr(config, name)
    if name in {"CLOUD_PORT", "HeartbeatConnectionType"}:
        from energy_core.integrations.heartbeat import connection

        return getattr(connection, name)
    if name == "create_heartbeat_client":
        from energy_core.integrations.heartbeat.client_factory import create_heartbeat_client

        return create_heartbeat_client
    if name == "parse_live_overview":
        from energy_core.integrations.heartbeat.live_overview import parse_live_overview

        return parse_live_overview
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
