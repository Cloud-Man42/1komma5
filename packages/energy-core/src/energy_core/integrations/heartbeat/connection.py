"""HeartBeat connection types and URL construction."""

from __future__ import annotations

from enum import StrEnum
from urllib.parse import urlparse

from energy_core.integrations.heartbeat.gridx_defaults import GRIDX_API_HOST, GRIDX_API_PORT
from energy_core.integrations.heartbeat.providers import HeartbeatBackendProvider

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


def provider_label(provider: HeartbeatBackendProvider | str) -> str:
    labels = {
        HeartbeatBackendProvider.ONEKOMMAFIVE: "1Komma5 Heartbeat (Sverige/EU)",
        HeartbeatBackendProvider.GRIDX: "GridX / my.1komma5.io",
    }
    return labels.get(HeartbeatBackendProvider(str(provider)), str(provider))


def apply_provider_defaults(
    provider: str,
    *,
    host: str = "",
    port: int = CLOUD_PORT,
    api_path: str = DEFAULT_API_PATH,
    auth_domain: str = "",
    auth_realm: str = "",
    auth_client_id: str = "",
) -> tuple[str, int, str, str, str, str]:
    """Fill empty account fields from provider-specific defaults."""
    from energy_core.integrations.heartbeat.gridx_defaults import (
        GRIDX_AUTH_CLIENT_ID,
        GRIDX_AUTH_DOMAIN,
        GRIDX_AUTH_REALM,
    )

    kind = HeartbeatBackendProvider(str(provider))
    if kind == HeartbeatBackendProvider.GRIDX:
        return (
            host.strip() or GRIDX_API_HOST,
            port if port else GRIDX_API_PORT,
            "" if api_path in ("", DEFAULT_API_PATH) else api_path.strip(),
            auth_domain.strip() or GRIDX_AUTH_DOMAIN,
            auth_realm.strip() or GRIDX_AUTH_REALM,
            auth_client_id.strip() or GRIDX_AUTH_CLIENT_ID,
        )
    return (
        host.strip(),
        port if port else CLOUD_PORT,
        api_path.strip() or DEFAULT_API_PATH,
        auth_domain.strip(),
        auth_realm.strip(),
        auth_client_id.strip(),
    )


def build_account_api_url(
    provider: str,
    connection_type: HeartbeatConnectionType | str,
    *,
    host: str = "",
    port: int = CLOUD_PORT,
    use_tls: bool = True,
    api_path: str = DEFAULT_API_PATH,
) -> str | None:
    """Build API base URL for a Heartbeat account (1Komma5 or GridX)."""
    kind = HeartbeatBackendProvider(str(provider))
    if kind == HeartbeatBackendProvider.GRIDX:
        resolved_host, resolved_port, resolved_path, _, _, _ = apply_provider_defaults(
            provider,
            host=host,
            port=port,
            api_path=api_path,
        )
        scheme = "https" if use_tls else "http"
        default_port = 443 if use_tls else 80
        port_suffix = "" if resolved_port in (0, default_port) else f":{resolved_port}"
        if resolved_host.startswith("http://") or resolved_host.startswith("https://"):
            base = resolved_host.rstrip("/")
        else:
            base = f"{scheme}://{resolved_host}{port_suffix}"
        return f"{base}{normalize_api_path(resolved_path)}"

    resolved_host = host
    if HeartbeatConnectionType(str(connection_type)) == HeartbeatConnectionType.CLOUD and not resolved_host:
        resolved_host = CLOUD_HOST
    return build_heartbeat_api_url(
        connection_type,
        host=resolved_host,
        port=port,
        use_tls=use_tls,
        api_path=api_path,
    )
