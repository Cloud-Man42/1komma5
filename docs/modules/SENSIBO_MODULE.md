# Sensibo Climate Module

**Module ID:** `integration.sensibo`  
**Type:** External read-only climate integration  
**Publisher:** `emic-official` (OFFICIAL)

## Purpose

Monitor Sensibo-connected climate devices through EMIC's isolated third-party runtime. Publishes normalized read-only HVAC state into EMIC's generic climate API.

## Capabilities (read-only)

- `hvac.read_temperature`
- `hvac.read_humidity`
- `hvac.read_state`
- `hvac.read_target_temperature`
- `hvac.read_status`

No control capabilities are exposed in Sprint E.

## Permissions

| Permission | Scope |
|------------|-------|
| `network.external` | `home.sensibo.com` only |
| `secrets.read_own` | Site-scoped Sensibo API key |
| `device.read` | Publish climate readings |

## Configuration

| Field | Description |
|-------|-------------|
| `credential_ref` | Secret reference (default `api_key`) |
| `poll_interval_seconds` | 60–3600 (default 300) |
| `selected_device_ids` | Optional subset of discovered Sensibo pod IDs |

Configure via Store install wizard or `PUT /api/sites/{slug}/modules/integration.sensibo/external-config`.

## Runtime authorization

Production requires an exact runtime pilot authorization grant (module, version, artifact SHA-256, publisher, site). Global `THIRD_PARTY_RUNTIME_ENABLED` remains `false`.

## Known limitations

- Read-only — no temperature/mode/power control (Sprint F)
- Requires admin Store access
- Sensibo API availability affects data freshness
