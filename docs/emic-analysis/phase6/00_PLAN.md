# Phase 6 — Vehicle & EV Charger Admin Auth

**Deployed:** 2026-09-03 to `http://192.168.50.54`

## Delivered

| Item | Change |
|------|--------|
| **EV charger mutations** | Admin token required on create/update/delete/sync/control/override/test-connection |
| **Vehicle mutations** | Admin token on sync, config, login, commands, integration actions, session patch |
| **Frontend** | `adminFetch()` for all above API helpers |
| **Integration health UX** | Alert when `consecutive_failures >= 3` or status ≠ ok |

## Admin-protected routes (new)

| Area | Methods |
|------|---------|
| `/api/sites/{slug}/ev-chargers` | POST |
| `/api/sites/{slug}/ev-chargers/*` | PUT, DELETE, PATCH, POST (sync, control, override, test) |
| `/api/sites/{slug}/vehicles/sync` | POST |
| `/api/sites/{slug}/vehicles/{id}` | PATCH |
| `/api/sites/{slug}/vehicles/integration/*` | PUT, POST |
| `/api/sites/{slug}/vehicles/*/commands/*` | POST |
| `/api/sites/{slug}/vehicles/*/charge-sessions/{id}` | PATCH |

GET/read endpoints remain open when token is set (dashboard, Pi, diagnostics).

## Operator note

Enter admin token on `/config` before EV setup, Mercedes config, charger control, or vehicle commands when `EMIC_ADMIN_TOKEN` is configured on the server.
