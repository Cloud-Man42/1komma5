"""Read the live charger status straight from the adapter.

Diagnostic for the case where EMIC reports CHARGING_STABLE while the charger
draws nothing: it prints the connector state the state machine acts on, which is
not exposed through the bridge-status API.

Usage (inside the backend container):
    python scripts/probe_charger_status.py [charger_id]
"""

from __future__ import annotations

import asyncio
import sys

from energy_core.chargers.framework.factory import ChargerAdapterFactory
from energy_core.chargers.framework.legacy_bridge import LegacyControlBridge
from energy_core.config import get_settings
from energy_core.db.ev_charger_repo import EvChargerRepository
from energy_core.db.session import create_engine, create_session_factory


def _find_client(root: object, depth: int = 0) -> object | None:
    """Walk the wrapper chain for the object holding get_chargepoint_status."""
    if depth > 8 or root is None:
        return None
    print(f"  chain[{depth}]={type(root).__name__}")
    if hasattr(root, "get_chargepoint_status"):
        return root
    for name in ("_client", "_adapter", "_inner", "_controller", "_impl"):
        found = _find_client(getattr(root, name, None), depth + 1)
        if found is not None:
            return found
    return None


async def main(charger_id: int) -> None:
    settings = get_settings()
    engine = create_engine(settings)
    factory = create_session_factory(engine)

    async with factory() as session:
        charger = await EvChargerRepository(session).get_by_id(charger_id)
        if charger is None:
            print(f"charger {charger_id} not found")
            return

        adapter = LegacyControlBridge(ChargerAdapterFactory.from_charger_model(charger))
        status = await adapter.get_status()
        print(f"charger_id={charger.id} name={charger.name}")
        print(f"  connected={status.connected}")
        print(f"  vehicle_connected={status.vehicle_connected}")
        print(f"  charging={status.charging}")
        print(f"  current_limit_a={status.current_limit_a}")
        print(f"  db.smart_charging_state={charger.smart_charging_state}")
        print(f"  db.last_charging_action={charger.last_charging_action}")
        print(f"  db.last_requested_current_a={charger.last_requested_current_a}")

        # The OCPP connector state distinguishes "the car refuses" (SuspendedEV)
        # from "no transaction was ever started" (Preparing/Available).
        client = _find_client(adapter)
        if client is None:
            print("  raw: adapter chain does not expose a Charge Amps client")
            return
        payload = await client.get_chargepoint_status()
        print(f"  raw.chargepoint_status={payload}")
        print(f"  raw.connector_settings={await client.get_connector_settings(force=True)}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 4))
