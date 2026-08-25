"""Heartbeat client wrapper that captures API observations."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

import httpx

from energy_core.heartbeat.discovery.models import HeartbeatApiObservation
from energy_core.heartbeat.discovery.redaction import redact_headers
from energy_core.heartbeat.discovery.schema_fingerprint import (
    KNOWN_EV_KEYS,
    KNOWN_WALLBOX_KEYS,
    schema_fingerprint,
    unknown_fields,
)
from energy_core.heartbeat_client import HeartbeatClient


class ObservingHeartbeatClient:
    """Wrap HeartbeatClient and record each HTTP call for discovery diagnostics."""

    def __init__(self, client: HeartbeatClient) -> None:
        self._client = client
        self.observations: list[HeartbeatApiObservation] = []

    async def _observe(
        self,
        method: str,
        path: str,
        *,
        fetch: Any,
        known_keys: frozenset[str] | None = None,
    ) -> Any:
        started = datetime.now(UTC)
        t0 = time.perf_counter()
        status_code = 200
        raw: dict[str, Any] | list[Any] | None = None
        error: str | None = None
        try:
            raw = await fetch()
            if isinstance(raw, dict):
                parsed = {"keys": list(raw.keys())[:20]}
            elif isinstance(raw, list):
                parsed = {"count": len(raw), "sample_keys": list(raw[0].keys())[:10] if raw else []}
            else:
                parsed = {"type": type(raw).__name__}
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            error = str(exc)
            try:
                raw = exc.response.json()
            except Exception:
                raw = {"error": exc.response.text[:500]}
            parsed = {"http_error": status_code}
            self._record(method, path, started, t0, status_code, raw, parsed, known_keys, error)
            raise
        except Exception as exc:
            status_code = 0
            error = str(exc)
            parsed = {"error": error}
            self._record(method, path, started, t0, status_code, raw, parsed, known_keys, error)
            raise

        self._record(method, path, started, t0, status_code, raw, parsed, known_keys, error)
        return raw

    def _record(
        self,
        method: str,
        path: str,
        started: datetime,
        t0: float,
        status_code: int,
        raw: Any,
        parsed: dict[str, Any],
        known_keys: frozenset[str] | None,
        error: str | None,
    ) -> None:
        duration_ms = int((time.perf_counter() - t0) * 1000)
        unk: tuple[str, ...] = ()
        fingerprint = ""
        if raw is not None:
            fingerprint = schema_fingerprint(raw)
            if known_keys is not None:
                if isinstance(raw, list) and raw:
                    unk = unknown_fields(raw[0], known_keys)
                elif isinstance(raw, dict):
                    unk = unknown_fields(raw, known_keys)
        self.observations.append(
            HeartbeatApiObservation(
                method=method,
                path=path,
                status_code=status_code,
                started_at=started,
                duration_ms=duration_ms,
                request_headers_redacted={"Authorization": "***REDACTED***", "Accept": "application/json"},
                response_headers_redacted={},
                raw_json=raw if isinstance(raw, (dict, list)) else None,
                parsed_summary=parsed,
                unknown_fields=unk,
                schema_fingerprint=fingerprint,
                error=error,
            )
        )

    async def list_evs(self, system_id: str) -> list[dict[str, Any]]:
        data = await self._observe(
            "GET",
            f"/v1/systems/{system_id}/devices/evs",
            fetch=lambda: self._client.list_evs(system_id),
            known_keys=KNOWN_EV_KEYS,
        )
        return data if isinstance(data, list) else []

    async def list_wallboxes(self, system_id: str) -> list[dict[str, Any]]:
        data = await self._observe(
            "GET",
            f"/v1/systems/{system_id}/devices/ev-chargers",
            fetch=lambda: self._client.list_wallboxes(system_id),
            known_keys=KNOWN_WALLBOX_KEYS,
        )
        return data if isinstance(data, list) else []

    async def list_charging_modes(self, system_id: str) -> list[Any]:
        return await self._observe(
            "GET",
            f"/v1/sites/{system_id}/assets/evs/displayed-ev-charging-modes",
            fetch=lambda: self._client.list_charging_modes(system_id),
            known_keys=frozenset({"displayedEvChargingModes"}),
        )

    async def fetch_ems_settings(self, system_id: str) -> dict[str, Any]:
        data = await self._observe(
            "GET",
            f"/v1/systems/{system_id}/ems/actions/get-settings",
            fetch=lambda: self._client.fetch_ems_settings(system_id),
            known_keys=frozenset({"devices", "settings", "activeChargingMode"}),
        )
        return data if isinstance(data, dict) else {}

    async def fetch_live_overview(self, system_id: str) -> dict[str, Any]:
        data = await self._observe(
            "GET",
            f"/v3/systems/{system_id}/live-overview",
            fetch=lambda: self._client.fetch_live_overview(system_id),
            known_keys=frozenset({"liveHeroView", "evChargersAggregated", "summaryCards"}),
        )
        return data if isinstance(data, dict) else {}

    async def fetch_optimizations(self, system_id: str, *, from_iso: str, to_iso: str) -> list[dict[str, Any]]:
        data = await self._observe(
            "GET",
            f"/v1/heartbeat-ai/optimizations?systemId={system_id}",
            fetch=lambda: self._client.fetch_optimizations(system_id, from_iso=from_iso, to_iso=to_iso),
            known_keys=frozenset({"optimizations", "decisionType", "type"}),
        )
        return data if isinstance(data, list) else []
