"""Runtime security reactions to revocations and critical advisories."""



from __future__ import annotations



import logging

from typing import TYPE_CHECKING



from energy_core.platform.modules.governance.revocation_reader import RevocationReader

from energy_core.platform.modules.isolation.types import IsolatedRuntimeState, RuntimeEventType

from energy_core.platform.modules.marketplace.trust_cache import MarketplaceTrustCacheRepository

from energy_core.platform.modules.marketplace.types import MetadataHealth

from energy_core.platform.modules.supply_chain.advisory_policy import parse_advisory_bundle

from energy_core.platform.modules.supply_chain.types import SbomComponent, SecuritySeverity

from energy_core.platform.modules.supply_chain.vulnerability_matcher import highest_severity, match_vulnerabilities



if TYPE_CHECKING:

    from sqlalchemy.ext.asyncio import AsyncSession



    from energy_core.config import Settings

    from energy_core.platform.modules.isolation.manager import IsolatedModuleRuntimeManager



logger = logging.getLogger(__name__)





class RuntimeSecurityMonitor:

    """Stops/quarantines isolated runtimes affected by trusted revocations or CRITICAL advisories."""



    def __init__(self, session: AsyncSession, settings: Settings) -> None:

        self._session = session

        self._settings = settings

        self._revocations = RevocationReader(session)

        self._trust_cache = MarketplaceTrustCacheRepository(session)



    async def check_runtime(self, manager: IsolatedModuleRuntimeManager, runtime_instance_id: str) -> bool:

        record = await manager.get_runtime(runtime_instance_id)

        if record is None:

            return False

        if record.state not in {

            IsolatedRuntimeState.RUNNING,

            IsolatedRuntimeState.DEGRADED,

            IsolatedRuntimeState.READY,

            IsolatedRuntimeState.HANDSHAKING,

        }:

            return False

        if await self._check_revocation(manager, record):

            return True

        if await self._check_critical_advisory(manager, record):

            return True

        return False



    async def scan_active(self, manager: IsolatedModuleRuntimeManager) -> int:

        stopped = 0

        for record in await manager.list_runtimes():

            if await self.check_runtime(manager, record.runtime_instance_id):

                stopped += 1

        return stopped



    async def _check_revocation(self, manager: IsolatedModuleRuntimeManager, record) -> bool:

        ctx = await self._revocations.load_context(enabled=self._settings.marketplace_metadata_enabled)

        if ctx.metadata_health == MetadataHealth.INVALID.value:

            return False

        match = self._revocations.find_active_revocation(

            ctx,

            publisher_id=record.publisher_id,

            module_id=record.module_id,

        )

        if match is None:

            return False

        scope = "publisher" if match.publisher_id == record.publisher_id else "module"

        await self._stop_security_event(manager, record, reason=f"revocation:{scope}", event_scope=scope)

        return True



    async def _check_critical_advisory(self, manager: IsolatedModuleRuntimeManager, record) -> bool:

        if not self._settings.marketplace_metadata_enabled:

            return False

        row = await self._trust_cache.get_or_create()

        raw = self._trust_cache.parse_advisories(row)

        if raw is None:

            return False

        bundle = parse_advisory_bundle(raw)

        component = SbomComponent(

            name=record.module_id,

            version=record.version,

            purl=f"pkg:emic/{record.module_id}@{record.version}",

        )

        matches = match_vulnerabilities((component,), bundle.advisories)

        if highest_severity(matches) != SecuritySeverity.CRITICAL:

            return False

        await self._stop_security_event(manager, record, reason="advisory:CRITICAL", event_scope="advisory")

        return True



    async def _stop_security_event(

        self,

        manager: IsolatedModuleRuntimeManager,

        record,

        *,

        reason: str,

        event_scope: str,

    ) -> None:

        logger.warning(

            "runtime security stop runtime=%s module=%s scope=%s",

            record.runtime_instance_id,

            record.module_id,

            event_scope,

        )

        await manager.stop_runtime(record.runtime_instance_id, reason=reason)

        await manager._repo.transition(

            record.runtime_instance_id,

            to_state=IsolatedRuntimeState.QUARANTINED,

            last_error=reason,

            reason_codes=("SECURITY_POLICY", event_scope.upper()),

        )

        await manager._audit(

            runtime_instance_id=record.runtime_instance_id,

            event_type=RuntimeEventType.REVOCATION_STOP,

            module_id=record.module_id,

            site_id=record.site_id,

            detail={"scope": event_scope, "reason": reason},

        )


