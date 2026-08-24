# Mercedes me vehicle integration

EMIC reads live vehicle telemetry from Mercedes-Benz via the same OAuth2/PKCE + WebSocket + protobuf stack used by the community [mbapi2020](https://github.com/ReneNulschDE/mbapi2020) project (MIT).

## Architecture

- **Collector** owns the long-lived Mercedes connection through `VehicleIntegrationSupervisor`.
- **Backend** exposes read-only REST endpoints and stores encrypted credentials/tokens in `vehicle_provider_connections`.
- **Frontend** shows normalized vehicle state on `/sites/{slug}/vehicle` and admin/diagnostics under Konfiguration.
- Smart charging and Charge Amps Halo are unchanged in milestone 1; vehicle data is display-only.

## Phase 5: Halo correlation

When a site has a linked (or sole) Halo charger, EMIC compares Mercedes vehicle signals with Halo meter readings:

| Signal | Mercedes | Halo |
| --- | --- | --- |
| Plugged | `is_plugged_in` | `last_vehicle_connected` |
| Charging | `is_charging` | derived from power/current |
| Power | `charging_power_kw` | `last_actual_power_w` |

Results are stored in `vehicle_halo_correlation` with confidence (0–1) and status `ALIGNED`, `PARTIAL`, `MISMATCH`, or `UNAVAILABLE`. The fordonsvy shows the latest correlation when data exists.

## Phase 6: Charge sessions & energy sources

When Mercedes reports plug-in/out and Halo delivers metered kWh, EMIC tracks **vehicle charge sessions**:

| Field | Source |
| --- | --- |
| Plug/unplug, SoC, target SoC | Mercedes `VehicleState` |
| Delivered kWh, cost, attribution | Halo meter + site energy flows (same engine as EV accounting) |
| Identification confidence | Halo correlation at session start |

Tables: `vehicle_charge_sessions`, `vehicle_charging_intervals`. Collector runs `VehicleChargeSessionCoordinator` each poll cycle for enabled sites.

API:

- `GET /api/sites/{slug}/vehicles/{id}/charge-sessions`
- `GET /api/sites/{slug}/vehicles/{id}/charge-sessions/current`

Halo kWh is authoritative for billing; Mercedes SoC is used for progression and estimated battery delta only.

## Phase 7: Vehicle-aware SmartLaddning

When Mercedes integration is enabled and Halo correlation is trusted, EMIC feeds live vehicle needs into the smart charging engine:

| Input | Source | Used for |
| --- | --- | --- |
| Current SoC | Mercedes | Remaining energy need (estimated kWh) |
| Target SoC | Mercedes | Deadline urgency, solar plan deadline |
| Departure / ETA | Mercedes | `departure_time`, `deadline_at` on charging config |
| Required kWh | EMIC estimate (SoC gap × battery capacity) | Combined urgency with time-to-departure |

Collector and backend resolve `VehicleChargingContext` per linked Halo charger. If correlation confidence is low, data is stale, or the vehicle is unplugged, EMIC falls back to manual charger settings and Heartbeat inputs only.

API: vehicle fields on `GET .../energy-reasoning` (`vehicle_linked`, `vehicle_soc_pct`, `vehicle_required_energy_kwh`, etc.).

## Phase 8: Mercedes commands (feature flag)

Write commands are **disabled by default** (`commands_enabled=false`). Enable only after live EQE verification.

| Command | Protobuf | Notes |
| --- | --- | --- |
| Set target SoC | `ChargingConfigure.max_soc` or legacy `BatteryMaxSocConfigure` | EQE uses `CHARGING_CONFIGURE` |
| Start charging | `ChargingConfigure.START` | Requires `CHARGING_CONFIGURE` |
| Stop charging | `ChargingConfigure.STOP` | Requires `CHARGING_CONFIGURE` |

Verify against EQE before enabling in production:

```powershell
# Dry-run (capabilities + protobuf shape only)
python scripts/verify_mercedes_eqe_commands.py --site akarp --vin-suffix 3146

# Live command test (vehicle must be reachable; use current target SoC first)
python scripts/verify_mercedes_eqe_commands.py --site akarp --vin-suffix 3146 --execute set-target-soc --target-soc 80
```

API (requires `commands_enabled`):

- `POST /api/sites/{slug}/vehicles/{id}/commands/set-target-soc`
- `POST /api/sites/{slug}/vehicles/{id}/commands/start-charging`
- `POST /api/sites/{slug}/vehicles/{id}/commands/stop-charging`

Commands open a short-lived Mercedes WebSocket from the backend, send a `ClientMessage.commandRequest`, and close. Capabilities from REST discovery gate each action.

## Prerequisites

1. Mercedes me account with **two-factor authentication disabled** (`GOTO_LOGIN_OTP` is rejected).
2. `EMIC_SECRET_KEY` (Fernet key) configured in production for encrypted password/token storage.
3. Network egress to Mercedes EU endpoints (or the selected region).

## Auth flow

1. PKCE authorization against `https://id.mercedes-benz.com/as/authorization.oauth2`
2. CIAM username/password steps with persistent `CIAM.DEVICE` cookie / `X-Device-Id` header
3. Authorization code exchanged at `/as/token.oauth2`
4. Refresh via `/as/token.oauth2` with `grant_type=refresh_token` when less than 60 seconds remain

Passwords and tokens are encrypted at rest via `SecretBox` (`energy_core/secrets.py`).

## WebSocket flow

- URL (EU): `wss://websocket.emea-prod.mobilesdk.mercedes-benz.com/v2/ws`
- Headers include raw `Authorization: <access_token>`, `OUTPUT-FORMAT: PROTO`, app/session IDs
- Binary frames decode to `vehicle_events_pb2.PushMessage`
- Unknown attributes are logged once and ignored

## REST discovery

- `GET /v1/config` (preflight)
- `GET /v2/vehicles` (falls back to `GET /v1/vehicle/self/masterdata` → `assignedVehicles`)
- `GET /v1/vehicle/{vin}/capabilities`

## Capabilities and UI labels

Capabilities discovered from REST are stored per vehicle. Missing values render as **Ej tillgängligt** in the UI.

Freshness labels:

| Label | Meaning |
| --- | --- |
| LIVE | Measured telemetry within stale threshold |
| INAKTUELL | Stale or aged data |
| OFFLINE | Integration disconnected/backoff |
| UPPSKATTAT | Estimated/calculated quality |

## Known limitations (milestone 1)

- Read-only: `commands_enabled` defaults to `false`
- 2FA accounts are unsupported
- Repeated auth failures open a circuit breaker requiring manual reset in admin UI
- HTTP 429 triggers longest backoff step and `blocked_since` diagnostics
- Mercedes commands require explicit `commands_enabled` (phase 8, default off)

## Recovery procedure

1. Verify Mercedes account status and disable 2FA if enabled.
2. Confirm `EMIC_SECRET_KEY` has not changed since tokens were stored.
3. Open **Konfiguration → Integrations → Mercedes me**, re-save credentials, click **Logga in**.
4. Inspect `/api/sites/{slug}/vehicles/integration/status` for `connection_state`, `backoff_until`, and counters.
5. Restart collector if supervisor task stalled after circuit open.

## Updating when Mercedes changes backend

1. Compare upstream `mbapi2020` commits for auth, REST paths, headers, or protobuf changes.
2. Re-vendor affected `*_pb2.py` files and update `THIRD_PARTY_NOTICES.md`.
3. Run `.\test-windows.ps1` and verify against a live EQE before deploy.

## Manual EQE verification checklist

1. Enable integration and log in from Konfiguration.
2. Confirm vehicle appears with masked VIN in logs (`W1K***xxxx`).
3. Plug EQE into Halo and verify SoC, target SoC, range, plugged/charging state, and kW update in fordonsvyn within seconds.
4. Report advertised capabilities for phase 5+ planning.
