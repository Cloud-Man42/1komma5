"""Single Heartbeat live overview fetch per site per collector cycle."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from energy_core.performance.provider_metrics import record_provider_call

logger = logging.getLogger(__name__)


@dataclass
class SitePollContext:
    """Caches one live overview per site for a collector poll cycle."""

    client: Any
    _overviews: dict[str, dict] = field(default_factory=dict)

    async def live_overview(self, site) -> dict | None:
        if not site.external_system_id or self.client is None:
            return None
        if site.slug in self._overviews:
            return self._overviews[site.slug]
        import time

        start = time.perf_counter()
        success = True
        try:
            overview = await self.client.fetch_live_overview(site.external_system_id)
        except Exception:
            success = False
            logger.exception("Failed to fetch live overview for site %s", site.slug)
            overview = None
        latency_ms = (time.perf_counter() - start) * 1000.0
        record_provider_call("heartbeat_live_overview", latency_ms, success=success, site_id=site.id)
        if overview is not None:
            self._overviews[site.slug] = overview
        return overview
