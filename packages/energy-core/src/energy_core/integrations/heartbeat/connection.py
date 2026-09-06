"""HeartBeat connection types and URL construction."""

from __future__ import annotations

from enum import StrEnum
from urllib.parse import urlparse

CLOUD_HOST = "heartbeat.1komma5grad.com"
CLOUD_PORT = 443
DEFAULT_API_PATH = "/api"


class HeartbeatConnectionType(StrEnum):
    MOCK = "mock"
    CLOUD = "cloud"
    LOCAL = "local"


def normalize_api_path(path: str) -> str:
    cleaned = path.strip()
    if not cleaned:
        return ""
    if not cleaned.startswith("/"):
        cleaned = f"/{cleaned}"
    return cleaned.rstrip("/") or ""


def build_heartbeat_api_url(
    connection_type: HeartbeatConnectionType | str,
    *,
    host: str = "",
    port: int = CLOUD_PORT,
    use_tls: bool = True,
    api_path: str = DEFAULT_API_PATH,
) -> str | None:
    kind = HeartbeatConnectionType(str(connection_type))
    path = normalize_api_path(api_path)

    if kind == HeartbeatConnectionType.MOCK:
        return None

    if kind == HeartbeatConnectionType.CLOUD:
        base = f"https://{CLOUD_HOST}"
        if port not in (443, 0) and port != CLOUD_PORT:
            base = f"{base}:{port}"
        return f"{base}{path or DEFAULT_API_PATH}"

    host = host.strip()
    if not host:
        return None

    if host.startswith("http://") or host.startswith("https://"):
        parsed = urlparse(host)
        base = f"{parsed.scheme}://{parsed.netloc}"
        existing_path = (parsed.path or "").rstrip("/")
        return f"{base}{path or existing_path or DEFAULT_API_PATH}"

    scheme = "https" if use_tls else "http"
    default_port = 443 if use_tls else 80
    port_suffix = "" if port in (0, default_port) else f":{port}"
    return f"{scheme}://{host}{port_suffix}{path or DEFAULT_API_PATH}"


def connection_type_label(connection_type: HeartbeatConnectionType | str) -> str:
    labels = {
        HeartbeatConnectionType.MOCK: "Mock (syntetisk testdata)",
        HeartbeatConnectionType.CLOUD: "1Komma5 molntjänst",
        HeartbeatConnectionType.LOCAL: "Lokal gateway (IP/port)",
    }
    return labels.get(HeartbeatConnectionType(str(connection_type)), str(connection_type))
