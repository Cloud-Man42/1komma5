"""Recompute EV session totals from their stored intervals.

Repairs two things: sessions whose energy was scaled away by a charger meter
delta of zero, and intervals that re-counted a session from its start after a
collector restart. Run with --apply to write.

    uv run --all-packages python scripts/repair_ev_sessions.py          # preview
    uv run --all-packages python scripts/repair_ev_sessions.py --apply  # write
"""

import argparse
import asyncio

from energy_core.config import get_settings
from energy_core.db.session import create_engine, create_session_factory
from energy_core.ev_accounting.repair import repair_sessions


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write the recomputed totals")
    parser.add_argument("--site-id", type=int, default=None, help="limit to one site")
    args = parser.parse_args()

    settings = get_settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        repairs = await repair_sessions(
            session,
            site_id=args.site_id,
            dry_run=not args.apply,
        )

    if not repairs:
        print("Nothing to repair — stored totals already match their intervals.")
    else:
        header = (
            f"{'ID':>4}  {'STATUS':<10}  {'IVLS':>5}  {'DROPPED':>16}  "
            f"{'OLD kWh':>9}  {'NEW kWh':>9}  {'SOL':>7}  {'BATT':>7}  {'NÄT':>7}"
        )
        print(header)
        print("-" * len(header))
        for r in repairs:
            dropped = f"{r.removed_intervals} / {r.removed_kwh:.1f} kWh" if r.removed_intervals else "—"
            print(
                f"{r.session_id:>4}  {r.status:<10}  {r.interval_count:>5}  {dropped:>16}  "
                f"{r.old_total_kwh:>9.2f}  {r.new_total_kwh:>9.2f}  "
                f"{r.solar_direct_kwh:>7.2f}  {r.solar_battery_kwh + r.grid_battery_kwh:>7.2f}  "
                f"{r.grid_direct_kwh:>7.2f}"
            )
        verb = "Repaired" if args.apply else "Would repair"
        print(f"\n{verb} {len(repairs)} session(s).")
        if not args.apply:
            print("Re-run with --apply to write.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
