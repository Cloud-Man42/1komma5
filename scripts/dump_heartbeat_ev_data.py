"""Dump HeartBeat EV/charger details for a site."""
import asyncio
import json
import sys

from energy_core.config import Settings
from energy_core.db.session import create_engine, create_session_factory
from energy_core.heartbeat_client_factory import create_heartbeat_client

SYSTEM_ID = sys.argv[1] if len(sys.argv) > 1 else "ec892788-0a43-46a4-bd25-b4bbc22ab6e3"


async def main() -> None:
    settings = Settings()
    session_factory = create_session_factory(create_engine(settings))
    async with session_factory() as session:
        client = await create_heartbeat_client(session)
        if client is None:
            print("NO_CLIENT")
            sys.exit(1)
        evs = await client.list_evs(SYSTEM_ID)
        boxes = await client.list_wallboxes(SYSTEM_ID)
        ems = await client.fetch_ems_settings(SYSTEM_ID)
        overview = await client.fetch_live_overview(SYSTEM_ID)
        print("EMS", json.dumps(ems, indent=2)[:2000])
        print("EVS", json.dumps(evs, indent=2)[:4000])
        print("BOXES", json.dumps(boxes, indent=2)[:4000])
        ev_agg = overview.get("evChargersAggregated") or (overview.get("liveHeroView") or {}).get("evChargersAggregated")
        print("EV_AGG", json.dumps(ev_agg, indent=2)[:1000])


if __name__ == "__main__":
    asyncio.run(main())
