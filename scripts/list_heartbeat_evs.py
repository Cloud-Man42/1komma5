"""List HeartBeat EVs for akarp via production DB credentials on server."""
import asyncio
import sys

from energy_core.config import Settings
from energy_core.db.session import create_engine, create_session_factory
from energy_core.heartbeat_client_factory import create_heartbeat_client

SYSTEM_ID = "ec892788-0a43-46a4-bd25-b4bbc22ab6e3"


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
        print("EMS_MODE", (ems or {}).get("activeChargingMode"))
        for ev in evs:
            profile = ev.get("profile") or {}
            settings = ev.get("chargeSettings") or {}
            print(
                "EV",
                ev.get("id"),
                profile.get("name") or profile.get("manufacturer"),
                settings.get("chargingMode"),
                "charger",
                ev.get("assignedChargerId"),
            )
        for box in boxes:
            print(
                "BOX",
                box.get("gridxHardwareId") or box.get("id"),
                box.get("name"),
                "assignedEv",
                box.get("assignedEvId"),
            )


if __name__ == "__main__":
    asyncio.run(main())
