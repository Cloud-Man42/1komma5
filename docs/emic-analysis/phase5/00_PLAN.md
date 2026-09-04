# Phase 5 — Admin Auth Expansion & Vehicle Integration Health

**Deployed:** 2026-09-03 to `http://192.168.50.54`

## Delivered

| Item | Change |
|------|--------|
| **Admin auth (P0)** | `EMIC_ADMIN_TOKEN` required on site/spa/heartbeat/energy-control mutations |
| **Frontend** | `adminFetch()` for config mutations; token from `/config` Admin-token panel |
| **Mercedes health** | Vehicle supervisor writes `mercedes` provider per site |
| **ChargeFinder health** | Collector slow lane syncs global ChargeFinder status to vehicle-enabled sites |

## Admin-protected routes

| Route | Method |
|-------|--------|
| `/api/system/heartbeat-config` | PUT |
| `/api/sites` | POST |
| `/api/sites/{slug}` | PUT, DELETE |
| `/api/sites/{slug}/energy-config` | PUT |
| `/api/sites/{slug}/energy-control/settings` | PUT |
| `/api/sites/{slug}/energy-control/apply` | POST |
| `/api/sites/{slug}/spa/config` | PUT |
| `/api/sites/{slug}/spa/control/config` | PUT |
| `/api/sites/{slug}/spa/test-connection` | POST |
| `/api/sites/{slug}/spa/cleaning/run-now` | POST |
| `/api/apple-devices/*` | mutations (Phase 2) |

When `EMIC_ADMIN_TOKEN` is unset, routes remain open (dev/default).

## Providers tracked (extended)

| Provider | Lane | Source |
|----------|------|--------|
| `mercedes` | background | vehicle supervisor (REST + websocket) |
| `chargefinder` | slow | global status → per vehicle-enabled site |
