# SEMP — Smart Energy Management Protocol (EMIC Phase 1)

EMIC exposes a **Virtual EVSE** over HTTP using a SEMP-compatible surface so Heartbeat can
discover and read EV charger consumption. Phase 1 is **read-only reporting**: Halo physical
control remains via the existing Charge Amps bridge.

## Device contract

| Field | Value |
|-------|-------|
| Device type | `EVCharger` |
| Manufacturer | `EMIC` |
| Model | `Virtual EVSE` |
| Physical charger | Charge Amps Halo (linked by `chargeamp_charger_id`) |
| Control path | **Not via SEMP** — Halo bridge only |

## Discovery

```
GET /semp
```

Returns a list of SEMP device IDs for chargers with `virtual_evse_enabled=true`.

```json
{
  "devices": ["emic-evse-{charger_id}"]
}
```

## Device info

```
GET /semp/{deviceId}
```

```json
{
  "deviceId": "emic-evse-1",
  "deviceName": "Virtual EVSE (Charge Amps Halo)",
  "deviceType": "EVCharger",
  "deviceSerial": "emic-evse-1",
  "deviceVendor": "EMIC",
  "deviceModel": "Virtual EVSE",
  "maxPowerConsumption": 11000,
  "minPowerConsumption": 0,
  "maxPowerProduction": 0
}
```

## Device status

```
GET /semp/{deviceId}/DeviceStatus
```

Power is reported in **watts** (positive = consumption). State follows SEMP charging enum:

| State | Meaning |
|-------|---------|
| `Idle` | No vehicle / not charging |
| `Charging` | Active charging (`power_w > 0`) |
| `Finished` | Session ended, vehicle may still be connected |

```json
{
  "deviceId": "emic-evse-1",
  "emSignalsAccepted": "No",
  "powerConsumption": {
    "powerInfo": [
      {
        "averagePower": 10200,
        "timestamp": "2026-08-21T10:30:00Z"
      }
    ]
  },
  "status": "Charging",
  "timestamp": "2026-08-21T10:30:00Z"
}
```

## Device2EM (consumption snapshot)

```
GET /semp/{deviceId}/Device2EM
```

Same power values as `DeviceStatus` for consumers that poll Device2EM specifically.

## Polling

| Parameter | Default | Env |
|-----------|---------|-----|
| Heartbeat poll interval | 30 s | (Heartbeat-side) |
| EMIC power refresh | 30 s | Halo meter + bridge cycle |
| Stale threshold | 120 s | `virtual_evse_stale_seconds` |

## Authentication

Phase 1: **no auth** on `/semp` (same network as EMIC backend). Production deployments
should place EMIC behind the site LAN or reverse proxy with network ACLs.

## Phase 1 exclusions

- No `PlanningRequest` / EM control callbacks to EMIC
- No inverter or battery SEMP devices (Sungrow is Heartbeat-proxy telemetry only)
- No Modbus writes to physical inverter

See [`examples/`](examples/) for sample payloads.
