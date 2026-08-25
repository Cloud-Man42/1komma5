"""Dump HeartBeat EV/charger details for a site."""
import asyncio
import json
import sys
from pathlib import Path

from energy_core.config import Settings
from energy_core.db.session import create_engine, create_session_factory
from energy_core.heartbeat.discovery.redaction import redact_json
from energy_core.heartbeat_client_factory import create_heartbeat_client

SYSTEM_ID = sys.argv[1] if len(sys.argv) > 1 else "ec892788-0a43-46a4-bd25-b4bbc22ab6e3"
SAVE_FIXTURES = "--save-fixtures" in sys.argv
FIXTURE_DIR = Path(__file__).resolve().parents[1] / "packages" / "energy-core" / "tests" / "fixtures" / "heartbeat"


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
        now = __import__("datetime").datetime.now(__import__("datetime").UTC)
        opts = await client.fetch_optimizations(
            SYSTEM_ID,
            from_iso=(now - __import__("datetime").timedelta(hours=24)).isoformat(),
            to_iso=now.isoformat(),
        )
        print("EMS", json.dumps(ems, indent=2)[:2000])
        print("EVS", json.dumps(evs, indent=2)[:4000])
        print("BOXES", json.dumps(boxes, indent=2)[:4000])
        ev_agg = overview.get("evChargersAggregated") or (overview.get("liveHeroView") or {}).get("evChargersAggregated")
        print("EV_AGG", json.dumps(ev_agg, indent=2)[:1000])
        if SAVE_FIXTURES:
            FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
            FIXTURE_DIR.joinpath("ev_profiles.json").write_text(
                json.dumps(redact_json(evs), indent=2), encoding="utf-8"
            )
            FIXTURE_DIR.joinpath("wallboxes_empty.json" if not boxes else "wallboxes_with_assignment.json").write_text(
                json.dumps(redact_json(boxes), indent=2), encoding="utf-8"
            )
            FIXTURE_DIR.joinpath("ems_settings.json").write_text(
                json.dumps(redact_json(ems), indent=2), encoding="utf-8"
            )
            FIXTURE_DIR.joinpath("ai_optimizations.json").write_text(
                json.dumps(redact_json(opts), indent=2), encoding="utf-8"
            )
            FIXTURE_DIR.joinpath("live_overview.json").write_text(
                json.dumps(redact_json(overview), indent=2), encoding="utf-8"
            )
            print(f"Saved sanitized fixtures to {FIXTURE_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
