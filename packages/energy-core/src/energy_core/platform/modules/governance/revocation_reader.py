"""Read-only revocation adapter over Step 5C.1 trust cache."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.platform.modules.marketplace.trust_cache import MarketplaceTrustCacheRepository
from energy_core.platform.modules.marketplace.types import MetadataHealth, RevocationFreshness
from energy_core.platform.modules.governance.types import RevocationMatch


@dataclass(frozen=True, slots=True)
class RevocationContext:
    freshness: str
    metadata_health: str
    revocations: tuple[RevocationMatch, ...]


class RevocationReader:
    def __init__(self, session: AsyncSession) -> None:
        self._cache = MarketplaceTrustCacheRepository(session)

    async def load_context(self, *, enabled: bool) -> RevocationContext:
        view = await self._cache.build_status_view(enabled=enabled)
        row = await self._cache.get_or_create()
        raw = self._cache.parse_revocations(row)
        matches = self._parse_matches(raw)
        return RevocationContext(
            freshness=view.revocation_freshness.value,
            metadata_health=view.metadata_health.value,
            revocations=matches,
        )

    def find_active_revocation(
        self,
        context: RevocationContext,
        *,
        publisher_id: str | None = None,
        module_id: str | None = None,
    ) -> RevocationMatch | None:
        if context.metadata_health == MetadataHealth.INVALID.value:
            return None
        for item in context.revocations:
            if publisher_id and item.publisher_id == publisher_id:
                return item
            if module_id and item.module_id == module_id:
                return item
        return None

    @staticmethod
    def _parse_matches(raw: dict[str, Any] | None) -> tuple[RevocationMatch, ...]:
        if raw is None:
            return ()
        entries = raw.get("revocations") or []
        matches: list[RevocationMatch] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if str(entry.get("action", "REVOKE")).upper() != "REVOKE":
                continue
            matches.append(
                RevocationMatch(
                    revocation_id=str(entry.get("revocation_id", "")),
                    severity=entry.get("severity"),
                    scope=entry.get("scope"),
                    publisher_id=entry.get("publisher_id"),
                    module_id=entry.get("module_id"),
                )
            )
        return tuple(matches)
