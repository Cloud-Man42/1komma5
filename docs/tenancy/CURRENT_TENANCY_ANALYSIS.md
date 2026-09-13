# EMIC Current Tenancy Analysis

> Generated as part of multi-tenant logical isolation work.  
> Status: single-deployment, multi-site — **not multi-tenant**.

## 1. Executive Summary

EMIC isolates data today at the **site** boundary. Users are global; access is granted via `emic_user_site_access`. There is **no `tenant_id`** column anywhere in the schema. Authorization is applied inconsistently at the API layer; repositories and background jobs frequently call unscoped `list_all()`.

## 2. Current Architecture

```
EmicUser (global)
  ├── emic_user_roles → emic_roles (global catalog)
  ├── emic_user_site_access → sites
  └── emic_user_sessions

Site (global slug unique)
  ├── energy_readings, energy_hourly, energy_daily
  ├── ev_chargers, vehicles (via site_id chains)
  ├── spa (via energy_consumers)
  ├── solar_* tables
  ├── pricing / financial
  └── heartbeat_account_id → heartbeat_accounts (global pool)

Principal (runtime)
  user_id, roles, permissions, site_ids, auth_method
```

### Auth flow

1. Request → `resolve_principal()` in `backend/app/user_auth.py`
2. Session cookie → `SessionService.resolve_principal()` → load user + roles + site_access
3. Route deps: `require_authenticated` → `require_permission` → optional site check
4. Site helpers: `get_site_for_principal`, `filter_sites_for_principal` in `backend/app/site_access.py`

### Break-glass / legacy modes

- `emic_admin_token` bearer → `break_glass_principal()` (SUPER_ADMIN, `*`)
- Auth disabled → `legacy_open_principal()` (full access)

## 3. Entities Affected

### 3.1 Root entities (need direct `tenant_id`)

| Table | File | Notes |
|-------|------|-------|
| `sites` | `db/models/sites.py` | Primary boundary; slug globally unique today |
| `emic_users` | `db/models/users.py` | Global identity; membership via new `tenant_users` |
| `heartbeat_accounts` | `db/models/heartbeat.py` | Shared credential pool |
| `emic_auth_audit_events` | `db/models/users.py` | Auth audit |
| `emic_user_sessions` | `db/models/users.py` | Needs `active_tenant_id` |

### 3.2 Site-scoped (~59 tables with direct `site_id`)

Energy, EV, solar, spa, pricing, consumer, integration_health, etc. Inherit tenant via `sites.tenant_id` or denormalized `tenant_id` for RLS performance.

### 3.3 Indirect site-scoped (~25 tables)

Vehicle child tables, spa sessions, EV accounting — via FK chains to site-rooted entities.

### 3.4 Platform-global (may stay deployment-global)

| Category | Tables | Decision |
|----------|--------|----------|
| Marketplace | 7 tables | Platform catalog; optional tenant feature flags later |
| Module governance | 8 tables | Platform-global |
| RBAC catalog | permissions, roles | Global catalog; assignments become tenant-scoped |
| Chargefinder geo cache | 3 tables | Acceptable cross-tenant read-only cache |
| `collector_task_runs` | 1 | Add tenant_id for observability |

**Total tables:** ~111 ORM models across 29 modules.  
**Need tenant isolation for SaaS:** ~85–90 tables.

## 4. APIs Affected

### 4.1 Correctly site-scoped (partial)

- `backend/app/api/sites.py`
- `backend/app/api/readings.py`
- `backend/app/api/dashboard.py`
- `backend/app/api/snapshot.py`
- `backend/app/api/multi_site.py`
- `backend/app/api/mobile.py`
- `backend/app/api/integration_health.py`
- `backend/app/api/user_preferences.py`

### 4.2 Missing site membership check (IDOR risk)

- `vehicles.py`, `ev_chargers.py`, `spa.py`
- `solar_intelligence.py`, `solar_forecast.py`
- `price_engine.py`, `prices.py`
- `energy_control.py`, `site_modules.py`
- `heartbeat_bridge.py`, `climate.py`, `external_modules.py`

### 4.3 Global / unscoped admin

- `users.py`, `roles.py` — all users/sites
- `heartbeat_accounts.py` — global integration accounts
- `apple_devices.py`, `module_runtime.py`, `system.py`, `operations.py`

### 4.4 Device-token APIs (separate auth)

- `widget.py` — returns all sites to any device token
- `display.py` — SSE for any slug
- `semp.py` — no auth

## 5. Repository Anti-Patterns

| Location | Pattern |
|----------|---------|
| `db/repositories.py` | `SiteRepository.list_all()` |
| `backend/app/site_access.py` | `filter_sites_for_principal` loads all then filters in Python |
| `backend/app/user_auth.py` | `build_user_response` calls `list_all()` |
| `backend/app/api/users.py` | `list_all()` ×3 for site maps |
| `backend/app/api/widget.py` | `list_all()` ×3 |
| `collector/app/collector.py` | `list_all()` in ~15 collector loops |
| `platform/modules/orchestrator.py` | `list_all()` ×2 |
| `site_energy/orchestrator_service.py` | `list_all()` |
| `auth/bootstrap.py` | Grants bootstrap admin all sites |

## 6. Cache Affected

### Site-scoped (baseline)

```
emic:site:{site_id}:snapshot
emic:site:{site_id}:dashboard
emic:site:{site_id}:financial:{period}:{year}
emic:multisite:{sorted-slugs}:overview
emic:events:snapshot:{site_id}
```

### Not tenant-scoped (gaps)

- `emic:events:modules` — global pub/sub channel
- Marketplace trust cache — single global row
- Heartbeat LKG — account-scoped only
- In-process singletons — shared across requests

**Target prefix:** `tenant:{tenant_id}:...`

## 7. Background Jobs Affected

- `collector/app/collector.py` — fast/medium/slow lanes iterate all sites
- `platform/modules/orchestrator.py` — start/reconcile all sites
- `backend/app/main.py` — marketplace sync (deployment-global)
- Module event listener — global Redis channel

## 8. Realtime Affected

| Mechanism | Location | Scoping |
|-----------|----------|---------|
| SSE (display) | `api/display.py` | Site channel; device token not site-bound |
| Redis snapshot pub/sub | `cache/snapshot_pubsub.py` | Per site_id |
| Module pub/sub | `cache/module_pubsub.py` | Global |
| Mercedes WebSocket | collector | Per vehicle |

No SignalR. No app WebSocket for dashboards.

## 9. Exports Affected

No backend export endpoints. Client-side CSV in frontend components inherits API scoping gaps.

## 10. Frontend / PWA State

| Key | File | Issue |
|-----|------|-------|
| Site selection | `SiteSelectionProvider.tsx` | Server-backed; no tenant |
| `emic-theme` | `ThemeProvider.tsx` | Global |
| `emic_admin_token` | `adminAuth.ts` | Global |
| `energy-scene-v2` | `energySceneConfig.ts` | Single shared config |
| `emic:pi:lkg:{slug}` | `piDashboardStorage.ts` | Per-site (OK) |
| PWA SW | `public/sw.js` | Static assets only; skips `/api/` |

## 11. Security Risks

1. **IDOR** — slug-based routes without site membership check
2. **Global list_all** — missed route guard = cross-tenant leak when multi-tenant exists
3. **Device tokens** — widget/display see all sites
4. **SUPER_ADMIN** — deployment-wide god mode without tenant dimension
5. **No RLS** — application bug cannot be caught at DB layer
6. **Cache key collision** — shared Redis across tenants
7. **Connection pool** — future RLS context must not leak between requests

## 12. Migration Order

1. **PR2** — Fix site-level IDOR (no schema change)
2. **PR3** — Tenant tables + `tenant_id` on root entities + Henrik Home backfill
3. **PR4** — TenantContext + session APIs
4. **PR5** — Repository/API tenant scoping + denormalize high-volume tables
5. **PR6** — PostgreSQL RLS policies
6. **PR7** — Cache/jobs/realtime/secrets
7. **PR8** — Frontend workspace UX
8. **PR9** — Cross-tenant security tests + regression

### Default tenant migration

| Entity | Target |
|--------|--------|
| Tenant | `Henrik Home` (`slug: henrik-home`) |
| Sites | Åkarp, Danmark → Henrik Home |
| Users | Global identity + `tenant_users` membership |
| Roles/site access | Copied to tenant-scoped tables |
| Heartbeat accounts | Henrik Home |
| Energy history | Backfill via site join |

## 13. Existing Assumptions to Remove

- `sites.slug` globally unique → `(tenant_id, slug)` unique
- `username` / `email` globally unique → stays global (user is global identity)
- `SUPER_ADMIN` sees everything → split into platform + tenant admin
- Collector processes all sites → per-tenant loops
- Admin UI lists all users → current tenant members only
