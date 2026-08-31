"""Delete vehicle charge history that records nothing.

Removes closed charge sessions that never charged (no start, no intervals, no
energy) and state history rows written by a discovery, which hold no telemetry.
The charger's own history in `ev_charging_sessions` is never touched.

    uv run --all-packages python scripts/purge_vehicle_sessions.py          # preview
    uv run --all-packages python scripts/purge_vehicle_sessions.py --apply  # delete
"""

import argparse
import asyncio

from energy_core.config import get_settings
from energy_core.db.session import create_engine, create_session_factory
from energy_core.vehicles.sessions.cleanup import purge_empty_history


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="delete instead of previewing")
    parser.add_argument("--site-id", type=int, default=None, help="limit to one site")
    parser.add_argument(
        "--keep-state-rows",
        action="store_true",
        help="keep the empty vehicle_state_history rows",
    )
    args = parser.parse_args()

    settings = get_settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        result = await purge_empty_history(
            session,
            site_id=args.site_id,
            include_state_rows=not args.keep_state_rows,
            dry_run=not args.apply,
        )
        if args.apply:
            await session.commit()

    if result.total == 0:
        print("Nothing to purge — no empty charge sessions or state rows.")
    else:
        if result.sessions:
            header = f"{'ID':>4}  {'BIL':>4}  {'STATUS':<10}  {'ANSLUTEN':<20}  {'FRÅNKOPPLAD':<20}"
            print(header)
            print("-" * len(header))
            for s in result.sessions:
                ended = s.disconnected_at.strftime("%Y-%m-%d %H:%M") if s.disconnected_at else "—"
                print(
                    f"{s.session_id:>4}  {s.vehicle_id:>4}  {s.status:<10}  "
                    f"{s.connected_at.strftime('%Y-%m-%d %H:%M'):<20}  {ended:<20}"
                )
            print()
        verb = "Deleted" if args.apply else "Would delete"
        print(f"{verb} {len(result.sessions)} empty charge session(s) "
              f"and {result.state_rows} empty state history row(s).")
        if not args.apply:
            print("Re-run with --apply to delete.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
