# EMIC Module Store API

**Date:** 2026-09-08  
**Base path:** `/api/modules/store`  
**Auth:** Admin token required (all routes)

---

## Endpoints

### GET `/status`

Marketplace health, freshness, offline/stale/invalid states.

### GET `/`

Paginated catalog.

| Query | Type | Description |
|-------|------|-------------|
| `search` | string | Max 200 chars |
| `category` | string | Normalized category |
| `trust` | string | Publisher tier |
| `installed` | bool | Filter installed |
| `update_available` | bool | Filter updates |
| `compatible` | bool | Compatibility filter |
| `control_capable` | bool | Control filter |
| `official` | bool | OFFICIAL only |
| `page` | int | Page (default 1) |
| `page_size` | int | Max 100 |
| `sort` | string | `recommended`, `name`, `recently_updated`, `installed`, `security_status` |

### GET `/{module_id}`

Aggregated detail view model.

### GET `/{module_id}/releases`

Version list with security/install state.

### GET `/publishers`

Publisher directory projection.

### GET `/publishers/{publisher_id}`

Publisher profile.

### GET `/security`

Security center aggregates.

### POST `/{module_id}/{version}/preflight`

**Non-mutating** install evaluation.

Body:

```json
{
  "site_slug": "akarp",
  "config": {}
}
```

### POST `/{module_id}/{version}/install`

Delegates to existing staging/install pipeline after preflight check.

---

## View models

Primary types in `energy_core.platform.modules.store.types`:

- `StoreModuleSummary` — catalog card
- `StoreModuleDetail` — detail page
- `StorePreflightResponse` — install wizard
- `StoreSecurityCenterView` — security dashboard

All include `policy.decision`, `policy.reason_codes`, and `policy.explanation` from governance evaluation.

---

## Primary action enum

`INSTALL`, `UPDATE`, `INSTALLED`, `STAGED`, `SECURITY_REVIEW_REQUIRED`, `BLOCKED_BY_POLICY`, `RUNTIME_NOT_PERMITTED`, `REVOKED`, `INCOMPATIBLE`

Frontend must render these values; it must not compute them independently.
