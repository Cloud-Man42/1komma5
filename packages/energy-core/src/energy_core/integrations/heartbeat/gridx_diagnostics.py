"""Sanitized GridX connectivity diagnostics (no secrets)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from energy_core.integrations.heartbeat.gridx_client import GridXClient


@dataclass(frozen=True, slots=True)
class GridXProbeResult:
    path: str
    ok: bool
    status_code: int | None = None
    detail: str = ""


@dataclass(frozen=True, slots=True)
class GridXDiagnosticsReport:
    provider: str
    api_url: str
    system_id: str | None = None
    gateway_id: str | None = None
    token_ok: bool = False
    probes: list[GridXProbeResult] = field(default_factory=list)


async def run_gridx_diagnostics(
    client: GridXClient,
    *,
    provider: str,
    api_url: str,
    system_id: str | None = None,
    gateway_id: str | None = None,
) -> GridXDiagnosticsReport:
    probes: list[GridXProbeResult] = []

    async def _probe(label: str, call) -> None:
        try:
            result = await call()
            ok = bool(result)
            probes.append(GridXProbeResult(path=label, ok=ok, status_code=200 if ok else None))
        except Exception as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            probes.append(
                GridXProbeResult(
                    path=label,
                    ok=False,
                    status_code=status,
                    detail=str(exc)[:200],
                )
            )

    await _probe("/account", client.fetch_account)
    if system_id:
        await _probe(f"/systems/{system_id}", lambda: client.fetch_system(system_id))
        await _probe(f"/systems/{system_id}/live", lambda: client.fetch_live_overview(system_id))
    if gateway_id:
        await _probe(
            f"/gateways/{gateway_id}/appliances?listAll=true",
            lambda: client.fetch_gateway_appliances(gateway_id, list_all=True),
        )

    token_ok = any(p.path == "/account" and p.ok for p in probes)
    return GridXDiagnosticsReport(
        provider=provider,
        api_url=api_url,
        system_id=system_id,
        gateway_id=gateway_id,
        token_ok=token_ok,
        probes=probes,
    )
