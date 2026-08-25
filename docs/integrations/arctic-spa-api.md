# Arctic Spa / MyArcticSpa API

OpenAPI: https://api.myarcticspa.com/api-docs/myarcticspa-openapi.json  
Base URL: `https://api.myarcticspa.com`  
Auth: header `X-API-KEY` (never expose to frontend or logs)

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/v2/spa/status` | Live status (only read endpoint) |
| PUT | `/v2/spa/temperature` | Set setpointF |
| PUT | `/v2/spa/pumps/{pump}` | Control pumps 1–5 or all |
| PUT | `/v2/spa/lights` | Lights on/off |
| PUT | `/v2/spa/filter` | Filter settings |
| PUT | `/v2/spa/boost` | Boost mode |
| PUT | `/v2/spa/easymode` | Easy mode |
| PUT | `/v2/spa/sds` | SDS |
| PUT | `/v2/spa/yess` | YESS |
| PUT | `/v2/spa/fogger` | Fogger |
| PUT | `/v2/spa/blowers/{blower}` | Blowers |

## Status fields (GET /v2/spa/status)

| Field | EMIC mapping |
|-------|--------------|
| `connected` | online/offline |
| `temperatureF` | °C via `(F - 32) × 5/9` |
| `setpointF` | target °C |
| `pump1`–`pump5` | off / low / high |
| `filter_status` | Idle, Purge, Filtering, Suspended, Overtemperature, Resuming, Boost, Sanitize |
| `errors[]` | alarm list |

## API coverage vs EMIC needs

| Data | REST API | EMIC approach |
|------|----------|---------------|
| Status/temp/pumps | Yes | Direct from API |
| Heater on/off | No explicit field | Infer from `filter_status` + temp delta |
| Power W | **No** | Inferred from component states |
| Energy kWh | **No** | Integrate power over time locally |
| History | **No** | EMIC `consumer_samples` is source of truth |

## Rate limits

- HTTP 429 with header `x-ratelimit-limit` (requests/minute)
- Default poll interval: 60s
- Exponential backoff on 429/503
- Single-flight polling per consumer

## Inferensmodell (fase 1)

Configurable W profiles per site/spa:

- `heater_w` — when filter indicates heating (Filtering, Boost, Resuming, Overtemperature)
- `pump_low_w`, `pump_high_w` — per active pump
- `circulation_w` — when Filtering without high pumps

`energy_delta_wh = avg(power_prev, power_now) × elapsed_hours` (power in W, result in Wh)

Quality: `CALCULATED` (normal), `ESTIMATED` (gap > 2× poll interval), `MISSING` (offline).
