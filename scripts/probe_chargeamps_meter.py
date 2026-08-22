"""Read-only probe for Charge Amps meter/session fields. Never log credentials."""
import asyncio
import json
import os
import sys

from energy_core.chargers.charge_amps import build_chargeamps_controller
from energy_core.chargers.client import CHARGEAMPS_API_BASE, ChargeAmpsClient
from energy_core.chargers.meter_adapter import ChargeAmpsMeterAdapter


CHARGER_ID = os.getenv("CHARGEAMPS_PROBE_CHARGER_ID", "").strip()
if not CHARGER_ID:
    raise SystemExit("Set CHARGEAMPS_PROBE_CHARGER_ID")

# Candidate external API paths — probe only, not used in prod until verified
EXTERNAL_CANDIDATE_PATHS = (
    f"/chargepoints/{CHARGER_ID}/sessions",
    f"/chargepoints/{CHARGER_ID}/connectors/1/sessions",
    f"/chargepoints/{CHARGER_ID}/metervalues",
    f"/chargepoints/{CHARGER_ID}/connectors/1/metervalues",
    f"/chargepoints/{CHARGER_ID}/consumption",
)


async def probe_web() -> None:
    controller = build_chargeamps_controller(CHARGER_ID, use_mock=False)
    adapter = ChargeAmpsMeterAdapter.from_controller(controller)
    snapshot = await adapter.get_snapshot()
    print("WEB_SNAPSHOT", json.dumps({
        "cumulative_kwh": snapshot.cumulative_kwh,
        "power_w": snapshot.power_w,
        "is_charging": snapshot.is_charging,
        "vehicle_connected": snapshot.vehicle_connected,
        "ocpp_status": snapshot.ocpp_status,
        "source": snapshot.energy_source,
    }, default=str))


async def probe_external(api_key: str, email: str, password: str) -> None:
    client = ChargeAmpsClient(
        charger_id=CHARGER_ID,
        api_key=api_key,
        email=email,
        password=password,
    )
    status = await client.get_chargepoint_status(force=True)
    print("EXTERNAL_STATUS_KEYS", sorted(status.keys()) if isinstance(status, dict) else type(status))
    connectors = status.get("connectorStatuses") or status.get("connector_statuses") or []
    if connectors:
        print("EXTERNAL_CONNECTOR_KEYS", sorted(connectors[0].keys()) if isinstance(connectors[0], dict) else connectors[0])

    for path in EXTERNAL_CANDIDATE_PATHS:
        try:
            data = await client._request("GET", path)
            print("EXTERNAL_OK", path, "keys=", sorted(data.keys()) if isinstance(data, dict) else type(data))
        except Exception as exc:
            print("EXTERNAL_FAIL", path, type(exc).__name__, str(exc)[:120])


async def main() -> None:
    email = os.getenv("CHARGEAMPS_EMAIL", "")
    password = os.getenv("CHARGEAMPS_PASSWORD", "")
    api_key = os.getenv("CHARGEAMPS_API_KEY", "")

    if not email or not password:
        print("Set CHARGEAMPS_EMAIL and CHARGEAMPS_PASSWORD")
        sys.exit(1)

    print("Probing web API...")
    await probe_web()

    if api_key:
        print("Probing external API at", CHARGEAMPS_API_BASE)
        await probe_external(api_key, email, password)
    else:
        print("CHARGEAMPS_API_KEY not set — skipping external probe")


if __name__ == "__main__":
    asyncio.run(main())
