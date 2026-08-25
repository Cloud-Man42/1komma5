"""Minimal Heartbeat PATCH client for controlled write tests."""

from __future__ import annotations

from typing import Any

import httpx

from energy_core.heartbeat_client import HeartbeatClient


class HeartbeatWriteClient:
    """Isolated write operations — only used by write test service."""

    def __init__(self, client: HeartbeatClient) -> None:
        self._client = client

    async def patch_ev(
        self,
        system_id: str,
        ev_id: str,
        payload: dict[str, Any],
    ) -> tuple[int, Any]:
        path = f"/v1/systems/{system_id}/devices/evs/{ev_id}"
        url = f"{self._client._credentials.api_url.rstrip('/')}{path}"
        token = self._client._api_token
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=self._client._timeout) as http:
            response = await http.patch(url, headers=headers, json=payload)
            body: Any = None
            if response.content:
                try:
                    body = response.json()
                except Exception:
                    body = {"raw": response.text[:500]}
            return response.status_code, body
