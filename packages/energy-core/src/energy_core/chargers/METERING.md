# Charge Amps Halo — Metering (verified fields)

Internal reference for EV Energy Accounting. Do not expose credentials in logs.

## Energy reading priority

1. **Native session energy** — only if a verified session endpoint returns delivered kWh
2. **Meter delta** — `totalConsumptionKwh` at stop minus start (cumulative lifetime counter)
3. **Power integration** — phase currents or Heartbeat `ev_actual_power_w` over time

## Web API (`my.charge.space`) — VERIFIED

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/chargepoints/{charger_id}` | Status + connector meter fields |

**Connector fields used (connectorId=1):**

| Field | Type | Usage |
|-------|------|-------|
| `totalConsumptionKwh` | float | Cumulative meter; session = delta |
| `totalConsumptionRaw` | float | Raw counter fallback |
| `current1`, `current2`, `current3` | float | Phase current (A) during charge |
| `chargingCurrent` | object | `{current1, current2, current3}` |
| `isCharging` | bool | Active charging |
| `ocppStatus` | string | OCPP state (Available = no EV) |
| `userCurrent`, `currentCurrent` | float | Configured limit |

**Not verified for production use:** session history endpoints.

## External API v5 (`eapi.charge.space`) — PARTIAL

| Method | Path | Status |
|--------|------|--------|
| GET | `/chargepoints/{id}/status` | Verified (control) |
| GET | `/chargepoints/{id}/connectors/{n}/settings` | Verified (control) |

Session/meter-specific endpoints must be probed with `scripts/probe_chargeamps_meter.py` before use.
No session endpoints are wired in production code until verified.

## Data quality labels

- `MEASURED` — meter delta or native session total
- `CALCULATED` — attribution from site energy balance
- `ESTIMATED` — power integration
- `INCOMPLETE` — missing price or stale Heartbeat data
