"""Single Heartbeat live overview fetch per site per collector cycle."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from energy_core.db.heartbeat_account_repo import HeartbeatAccountRepository
from energy_core.performance.provider_metrics import record_provider_call

logger = logging.getLogger(__name__)


@dataclass
class SitePollContext:
    """Caches one live overview per site for a collector poll cycle."""

    clients_by_account: dict[int, Any] = field(default_factory=dict)
    default_client: Any | None = None
    _overviews: dict[str, dict] = field(default_factory=dict)

    @classmethod
    def from_clients(cls, clients_by_account: dict[int, Any]) -> SitePollContext:
        return cls(clients_by_account=clients_by_account, default_client=None)

    def client_for_site(self, site) -> Any | None:
        account_id = getattr(site, "heartbeat_account_id", None)
        if account_id is not None:
            return self.clients_by_account.get(account_id)
        if len(self.clients_by_account) == 1:
            return next(iter(self.clients_by_account.values()))
        return None

    async def live_overview(self, site) -> dict | None:
        system_id = HeartbeatAccountRepository.resolve_system_id(site)
        client = self.client_for_site(site)
        if not system_id or client is None:
            return None
        if site.slug in self._overviews:
            return self._overviews[site.slug]
        import time

        start = time.perf_counter()
        success = True
        try:
            overview = await client.fetch_live_overview(system_id)
        except Exception:
            success = False
            logger.exception("Failed to fetch live overview for site %s", site.slug)
            overview = None
        latency_ms = (time.perf_counter() - start) * 1000.0
        record_provider_call("heartbeat_live_overview", latency_ms, success=success, site_id=site.id)
        if overview is not None:
            self._overviews[site.slug] = overview
        return overview
