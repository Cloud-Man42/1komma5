"""Probe Charge Amps vehicle connection signals (no secrets logged)."""
import asyncio
import json
import os
import sys

from energy_core.chargers.charge_amps import build_chargeamps_controller
from energy_core.chargers.meter_adapter import ChargeAmpsMeterAdapter


CHARGER_ID = os.getenv("CHARGEAMPS_PROBE_CHARGER_ID", "").strip()
if not CHARGER_ID:
    raise SystemExit("Set CHARGEAMPS_PROBE_CHARGER_ID")


async def main() -> None:
    api_key = os.getenv("PROBE_API_KEY", os.getenv("CHARGEAMPS_API_KEY", ""))
    email = os.getenv("CHARGEAMPS_EMAIL", "")
    password = os.getenv("CHARGEAMPS_PASSWORD", "")

    meter = ChargeAmpsMeterAdapter.build(
        CHARGER_ID,
        api_key=api_key,
        email=email,
        password=password,
    )
    snapshot = await meter.get_snapshot()
    print(
        "METER",
        json.dumps(
            {
                "vehicle_connected": snapshot.vehicle_connected,
                "is_charging": snapshot.is_charging,
                "ocpp_status": snapshot.ocpp_status,
                "power_w": snapshot.power_w,
                "source": snapshot.energy_source,
                "uses_web": meter._web is not None,
            },
            default=str,
        ),
    )

    if meter._web is not None:
        data = await meter._web._request("GET", f"/chargepoints/{CHARGER_ID}")
        connectors = data.get("connectors") or []
        connector = connectors[0] if connectors else {}
        print(
            "WEB_CONNECTOR",
            json.dumps(
                {
                    key: connector.get(key)
                    for key in sorted(connector.keys())
                    if key
                    not in {
                        "defaultNfcTagId",
                    }
                },
                default=str,
            ),
        )

    controller = build_chargeamps_controller(
        CHARGER_ID,
        api_key=api_key,
        email=email,
        password=password,
        use_mock=False,
    )
    status = await controller.get_status()
    print(
        "STATUS",
        json.dumps(
            {
                "vehicle_connected": status.vehicle_connected,
                "charging": status.charging,
                "connected": status.connected,
            },
            default=str,
        ),
    )

    external = getattr(controller, "_adapter", None)
    if external is not None:
        payload = await external._client.get_chargepoint_status(force=True)
        connectors = payload.get("connectorStatuses") or payload.get("connector_statuses") or []
        connector = connectors[0] if connectors else {}
        print("EXTERNAL_CONNECTOR", json.dumps(connector, default=str))


if __name__ == "__main__":
    asyncio.run(main())
