"""Heartbeat installation discovery against authenticated API clients."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.integrations.heartbeat.client_factory import create_heartbeat_client
from energy_core.integrations.heartbeat.gridx_client import GridXClient
from energy_core.integrations.heartbeat.providers import HeartbeatBackendProvider
from energy_core.integrations.heartbeat.serial_matcher import SerialMatchResult, match_serial

_ONEKOMMAFIVE_LIST_PATHS = ("/v1/systems", "/v1/sites")


@dataclass(frozen=True, slots=True)
class HeartbeatInstallation:
    name: str | None = None
    system_id: str | None = None
    site_id: str | None = None
    asset_id: str | None = None
    device_id: str | None = None
    gateway_id: str | None = None
    serial_number: str | None = None


@dataclass(frozen=True, slots=True)
class HeartbeatDiscoveryReport:
    account_id: int
    provider: str
    api_url: str | None
    authentication_ok: bool
    installations: tuple[HeartbeatInstallation, ...] = field(default_factory=tuple)
    raw_paths_probed: tuple[str, ...] = field(default_factory=tuple)
    serial_matches: tuple[SerialMatchResult, ...] = field(default_factory=tuple)


def _first_str(node: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = node.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _installation_from_node(node: dict[str, Any]) -> HeartbeatInstallation:
    return HeartbeatInstallation(
        name=_first_str(node, "name", "displayName", "title"),
        system_id=_first_str(node, "systemId", "system_id", "id"),
        site_id=_first_str(node, "siteId", "site_id"),
        asset_id=_first_str(node, "assetId", "asset_id"),
        device_id=_first_str(node, "deviceId", "device_id", "gridxHardwareId"),
        gateway_id=_first_str(node, "gatewayId", "gateway_id"),
        serial_number=_first_str(node, "serialNumber", "serial_number", "serial", "gridxHardwareId"),
    )


def _installations_from_payload(payload: Any) -> list[HeartbeatInstallation]:
    installations: list[HeartbeatInstallation] = []
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                installations.append(_installation_from_node(item))
    elif isinstance(payload, dict):
        for key in ("systems", "sites", "installations", "items", "data"):
            nested = payload.get(key)
            if isinstance(nested, list):
                for item in nested:
                    if isinstance(item, dict):
                        installations.append(_installation_from_node(item))
        if not installations and any(k in payload for k in ("id", "systemId", "name")):
            installations.append(_installation_from_node(payload))
    return installations


async def _probe_paths(client: Any, paths: tuple[str, ...]) -> tuple[list[Any], tuple[str, ...]]:
    candidates: list[Any] = []
    probed: list[str] = []
    for path in paths:
        try:
            result = await client._request("GET", path)
            candidates.append(result)
            probed.append(path)
        except Exception:
            continue
    return candidates, tuple(probed)


async def _discover_onekommafive(client: Any) -> tuple[list[HeartbeatInstallation], tuple[str, ...], list[Any]]:
    candidates, probed = await _probe_paths(client, _ONEKOMMAFIVE_LIST_PATHS)
    installations: list[HeartbeatInstallation] = []
    for candidate in candidates:
        installations.extend(_installations_from_payload(candidate))
    return installations, probed, candidates


async def _discover_gridx(client: GridXClient) -> tuple[list[HeartbeatInstallation], tuple[str, ...], list[Any]]:
    candidates: list[Any] = []
    probed: list[str] = []

    account_payload = await client.fetch_account()
    candidates.append(account_payload)
    probed.append("/account")

    systems_payload = None
    try:
        systems_payload = await client._request("GET", "/systems")
        candidates.append(systems_payload)
        probed.append("/systems")
    except Exception:
        systems_payload = None

    installations = _installations_from_payload(systems_payload or account_payload)

    for installation in list(installations):
        system_id = installation.system_id
        if not system_id:
            continue
        try:
            detail = await client.fetch_system(system_id)
            candidates.append(detail)
            probed.append(f"/systems/{system_id}")
            enriched = _installation_from_node(detail)
            gateway_id = enriched.gateway_id or _first_str(detail, "gatewayId", "gateway_id")
            if gateway_id:
                try:
                    appliances = await client.fetch_gateway_appliances(gateway_id, list_all=True)
                    candidates.append({"gatewayId": gateway_id, "appliances": appliances})
                    probed.append(f"/gateways/{gateway_id}/appliances")
                except Exception:
                    pass
        except Exception:
            continue

    if not installations:
        installations = _installations_from_payload({"candidates": candidates})
    return installations, tuple(probed), candidates


async def discover_account_installations(
    session: AsyncSession,
    account_id: int,
    *,
    provider: str,
    api_url: str | None = None,
) -> HeartbeatDiscoveryReport:
    """Discover visible installations for an authenticated account."""
    client = await create_heartbeat_client(session, account_id=account_id)
    if client is None:
        return HeartbeatDiscoveryReport(
            account_id=account_id,
            provider=provider,
            api_url=api_url,
            authentication_ok=False,
        )

    if isinstance(client, GridXClient):
        installations, probed, candidates = await _discover_gridx(client)
    else:
        installations, probed, candidates = await _discover_onekommafive(client)

    return HeartbeatDiscoveryReport(
        account_id=account_id,
        provider=provider,
        api_url=api_url or getattr(getattr(client, "_credentials", None), "api_url", None),
        authentication_ok=True,
        installations=tuple(installations),
        raw_paths_probed=probed,
    )


async def discover_system_id_for_serial(
    session: AsyncSession,
    account_id: int,
    serial: str,
) -> SerialMatchResult:
    """Probe list endpoints and match a hardware serial."""
    client = await create_heartbeat_client(session, account_id=account_id)
    if client is None:
        return SerialMatchResult(serial=serial, found=False)

    if isinstance(client, GridXClient):
        _, _, candidates = await _discover_gridx(client)
    else:
        _, _, candidates = await _discover_onekommafive(client)

    return match_serial({"candidates": candidates}, serial)


async def discover_serial_for_account(
    session: AsyncSession,
    account_id: int,
    serial: str,
    *,
    provider: str,
    api_url: str | None = None,
) -> HeartbeatDiscoveryReport:
    """Full discovery report with explicit serial match."""
    report = await discover_account_installations(
        session,
        account_id,
        provider=provider,
        api_url=api_url,
    )
    serial_result = match_serial(
        {"candidates": [inst.__dict__ for inst in report.installations]},
        serial,
    )
    if not serial_result.found:
        client = await create_heartbeat_client(session, account_id=account_id)
        if client is not None:
            if isinstance(client, GridXClient):
                _, _, candidates = await _discover_gridx(client)
            else:
                _, _, candidates = await _discover_onekommafive(client)
            serial_result = match_serial({"candidates": candidates}, serial)

    return HeartbeatDiscoveryReport(
        account_id=report.account_id,
        provider=report.provider,
        api_url=report.api_url,
        authentication_ok=report.authentication_ok,
        installations=report.installations,
        raw_paths_probed=report.raw_paths_probed,
        serial_matches=(serial_result,) if serial else report.serial_matches,
    )
