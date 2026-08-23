"""Quick read-only integration check for Charge Amps web API."""

import asyncio
import os

from energy_core.chargers.charge_amps import build_chargeamps_controller


async def main() -> None:
    charger_id = os.environ.get("CHARGEAMPS_PROBE_CHARGER_ID", "").strip()
    if not charger_id:
        raise SystemExit("Set CHARGEAMPS_PROBE_CHARGER_ID")
    controller = build_chargeamps_controller(
        charger_id,
        email=os.environ["CHARGEAMPS_EMAIL"],
        password=os.environ["CHARGEAMPS_PASSWORD"],
        use_mock=False,
    )
    status = await controller.get_status()
    print("connected", status.connected)
    print("vehicle_connected", status.vehicle_connected)
    print("current_limit_a", status.current_limit_a)
    print("charging", status.charging)


if __name__ == "__main__":
    asyncio.run(main())
