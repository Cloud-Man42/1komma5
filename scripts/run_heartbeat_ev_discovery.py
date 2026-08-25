"""Run Heartbeat EV discovery for a site and print §60 report."""
import asyncio
import sys

from energy_core.config import Settings
from energy_core.db.ev_charger_repo import EvChargerRepository
from energy_core.db.session import create_engine, create_session_factory
from energy_core.heartbeat.bridge.service import HeartbeatEvBridgeService


async def main() -> None:
    slug = sys.argv[1] if len(sys.argv) > 1 else "akarp"
    settings = Settings()
    session_factory = create_session_factory(create_engine(settings))
    async with session_factory() as session:
        repo = EvChargerRepository(session)
        site = await repo.get_site_by_slug(slug)
        if site is None:
            print(f"Site not found: {slug}")
            sys.exit(1)
        service = HeartbeatEvBridgeService(session)
        try:
            result, run_id = await service.run_discovery(slug)
        except Exception as exc:
            print(f"DISCOVERY FAILED: {exc}")
            sys.exit(2)
        print(result.report_text)
        print(f"\nRun ID: {run_id}")


if __name__ == "__main__":
    asyncio.run(main())
