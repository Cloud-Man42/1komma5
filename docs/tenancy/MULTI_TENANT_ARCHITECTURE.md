# EMIC Multi-Tenant Architecture

Living document for logical tenant isolation in EMIC.

## 1. Goals

- **One platform, multiple tenants** — shared app, backend, PostgreSQL, codebase
- **Strict logical isolation** — defense-in-depth, not relying on developer discipline alone
- **Backward compatible** — Åkarp, Danmark, existing auth/RBAC/multi-site/PWA continue working
- **Future-ready** — optional dedicated DB per enterprise tenant without rewrite

## 2. Logical Tenant Isolation

```
Authenticated User
  → Tenant Membership (tenant_users)
  → Current Tenant Context (session.active_tenant_id)
  → Tenant Role / Permissions
  → Site Access (within tenant)
  → Tenant-scoped Application Query
  → PostgreSQL RLS
  → Database
```

## 3. Tenant Model

Table: `tenants`

| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| name | String | Internal name |
| display_name | String | UI label |
| slug | String | Unique; URL-safe |
| is_active | Boolean | Disable blocks workspace use |
| status | String | active, suspended, etc. |
| timezone | String | Default for tenant |
| default_currency | String | e.g. SEK |
| created_at, updated_at | DateTime | |

Future (not implemented): subscription_plan, billing_status, logo_url, theme, metadata.

## 4. Membership

**Global identity:** `emic_users` — login email/username unique deployment-wide.

**Tenant membership:** `tenant_users`

| Column | Notes |
|--------|-------|
| tenant_id | FK tenants |
| user_id | FK emic_users |
| is_active | |
| unique(tenant_id, user_id) | |

A user may belong to multiple tenants with different roles in each.

## 5. Tenant Context

Module: `energy_core.tenancy`

```python
@dataclass
class TenantContext:
    tenant_id: int
    tenant_slug: str
    tenant_name: str
    user_id: int
    tenant_user_id: int
    is_platform_admin: bool
```

- Created per HTTP request from session + membership
- Client `tenantId` never trusted without verification
- FastAPI dependency: `get_tenant_context()`
- Auto-select when user has exactly one tenant

## 6. Roles

### Platform roles (global)

| Role | Purpose |
|------|---------|
| PLATFORM_SUPER_ADMIN | Create/disable tenants, platform config |
| PLATFORM_SUPPORT | Audited limited cross-tenant support |

Stored on user via `platform_user_roles` or equivalent.

### Tenant roles (per membership)

| Role | Purpose |
|------|---------|
| TENANT_ADMIN | Users, sites, integrations within tenant |
| TENANT_OPERATOR | Operations, control |
| TENANT_USER | Standard access |
| TENANT_VIEWER | Read-only |

Assignments: `tenant_user_roles` → global `emic_roles` catalog.

Existing SUPER_ADMIN migrates to PLATFORM_SUPER_ADMIN + TENANT_ADMIN in default tenant.

## 7. Permissions

Global permission catalog unchanged (`energy_core.auth.permissions`).

Effective permissions = tenant role assignments for current tenant.

Platform permissions (e.g. `tenants.manage`) separate from tenant permissions.

## 8. Site Access

Table: `tenant_user_site_access`

- FK `tenant_user_id` + `site_id`
- Constraint: `site.tenant_id == tenant_user.tenant_id`
- Replaces direct `emic_user_site_access` for tenant-scoped access (legacy table migrated)

## 9. Data Ownership

### Direct `tenant_id`

- `sites`, `heartbeat_accounts`, `emic_auth_audit_events`
- High-volume: `energy_readings`, `site_live_snapshots`, `admin_audit_log`

### Via site FK

- EV, solar, spa, vehicles, pricing — tenant inferred from `sites.tenant_id`
- RLS policies JOIN through sites or use denormalized tenant_id on write

## 10. Database Model Changes

Migration `079_tenants_foundation.py`:

1. Create tenant tables
2. Add nullable `tenant_id` columns
3. Seed Henrik Home; backfill existing data
4. NOT NULL + indexes + FK constraints
5. Validation script

Slug uniqueness: `UNIQUE(tenant_id, slug)`.

## 11. PostgreSQL RLS

Application sets per transaction:

```sql
SELECT set_config('app.current_tenant_id', :tenant_id, true);
```

Policies on: sites, energy_readings, heartbeat_accounts, emic_auth_audit_events, tenant_users, tenant_user_site_access, site_live_snapshots, integration_health.

Platform bypass: `app.platform_bypass = 'true'` with audit — not default.

App DB user: **no BYPASSRLS**.

SQLite: app-layer enforcement; RLS tested on Postgres.

## 12. Connection / Session Tenant Context

- `SET LOCAL` scoped to transaction
- Pool checkout: reset session variables
- Test: alternating tenants on pooled connection

Module: `energy_core.tenancy.db_rls`

## 13. Cache Isolation

Prefix: `tenant:{tenantId}:site:{siteId}:...`

Updated in: `cache/service.py`, `snapshot_pubsub.py`, `module_pubsub.py`, `multi_site/service.py`.

## 14. Background Jobs

```python
for tenant in await tenant_repo.list_active():
    async with tenant_context(tenant.id):
        for site in await site_repo.list_for_tenant(tenant.id):
            ...
```

Locks: `tenant:{id}:heartbeat-sync`. Disabled tenants skipped.

## 15. Integrations

- `heartbeat_accounts.tenant_id` required
- Site may only reference account in same tenant
- Secret namespace: `tenant/{tenantId}/heartbeat/{accountId}`

## 16. Secret Storage

Metadata on encrypted credentials includes `tenant_id`. Retrieval validates tenant match.

## 17. Realtime

Channels: `tenant:{tenantId}`, `tenant:{tenantId}:site:{siteId}`.

Subscribe only after membership + site access validation.

## 18. PWA / Client State

localStorage keys prefixed: `tenant:{tenantId}:selectedSites`, etc.

On tenant switch: clear tenant UI state, reload sites/permissions.

On user switch: clear all tenant keys.

## 19. Exports

No backend ExportJob today. Client CSV uses scoped APIs.

Future exports: `tenant_id` column + download verification.

## 20. Audit

`emic_auth_audit_events.tenant_id` — nullable for platform events.

Tenant admin sees current tenant only. Platform admin: separate audited view.

## 21. Platform Admin

Routes: `/api/platform/tenants/*`

- Create tenant, disable tenant, health overview
- Cross-tenant access explicit and audited

UI: `/platform/tenants`

## 22. Tenant Admin

Existing `/admin/*` scoped to current tenant:

Users, Roles, Sites, Integrations, Audit, Settings, Health.

## 23. Migration

Default tenant: **Henrik Home** (`henrik-home`).

All existing sites, users, integrations, energy data assigned to Henrik Home.

No permanent `if tenant == "henrik-home"` in code.

## 24. Security

See [THREAT_MODEL.md](./THREAT_MODEL.md).

Cross-tenant tests: `backend/tests/test_tenant_security.py`.

RLS tests: `backend/tests/test_tenant_rls.py` (Postgres marker).

## 25. Tests

- 25+ cross-tenant IDOR scenarios
- RLS SELECT/INSERT/UPDATE/DELETE
- Connection pool safety
- Cache key isolation
- Tenant switch membership
- User switch state clear
- Regression: Åkarp, Danmark, PWA, kiosk, auth, RBAC

## 26. Operational Considerations

- Rate limiting: per-tenant (future)
- Tenant health dashboard
- Disable tenant: block login/workspace; pause jobs; retain data
- Structured logs: tenantId, userId, siteId, correlationId — no secrets

## 27. Future Dedicated DB Option

Architecture allows:

| Tier | Deployment |
|------|------------|
| Standard | Shared PostgreSQL + RLS |
| Enterprise | Dedicated PostgreSQL, same codebase |
| Critical | Dedicated EMIC instance + DB |

Avoid hardcoding single-DB assumptions in business logic; use `TenantContext` + connection factory abstraction.

## 28. API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/tenants/mine` | List user workspaces |
| POST | `/api/tenants/select` | Set active tenant |
| GET | `/api/tenants/current` | Current tenant + permissions |
| GET/POST | `/api/platform/tenants` | Platform admin CRUD |

## 29. Implementation Status

Phases 0–8 implemented on branch (2026-09-13):

| Phase | Status | Notes |
|-------|--------|-------|
| PR1 Analysis docs | Done | `CURRENT_TENANCY_ANALYSIS.md`, `THREAT_MODEL.md`, this doc |
| PR2 Site IDOR fixes | Done | `authorized_site()` on slug routes; widget/display ACL |
| PR3 Tenant schema | Done | Alembic 079, Henrik Home backfill, tenant membership tables |
| PR4 TenantContext | Done | Session `active_tenant_id`, Principal extension, `/api/tenants/*` |
| PR5 API scoping | Done | `list_for_tenant`, admin users scoped, site filter by tenant |
| PR6 PostgreSQL RLS | Done | Alembic 080, `bind_tenant_to_session`, pool reset, bypass path |
| PR7 Cache/jobs | Done | Tenant cache keys, collector tenant loops, pub/sub channel helpers |
| PR8 Frontend UX | Done | `TenantSelectionProvider`, `/workspaces`, header switcher, `/platform/tenants` |
| PR9 Security tests | Done | 25+ cross-tenant tests in `test_tenant_security.py`; RLS tests (Postgres-only) |

---

## EMIC MULTI-TENANT LOGICAL ISOLATION STATUS

**Date:** 2026-09-13  
**Deployment model:** Shared PostgreSQL with logical tenant isolation (RLS on prod; app-layer on SQLite tests)

### Security stack (implemented)

1. Global user identity + `tenant_users` membership
2. Active tenant in server session (`emic_user_sessions.active_tenant_id`)
3. `Principal.tenant_id` / `tenant_user_id` / `platform_roles`
4. Site ACL within tenant (`tenant_user_site_access`)
5. Repository queries filtered by tenant (`list_for_tenant`)
6. PostgreSQL RLS on `sites`, `energy_readings`, `heartbeat_accounts`, `emic_auth_audit_events`, `tenant_users`
7. Tenant-prefixed cache keys and pub/sub channels

### Migration

- Default tenant **Henrik Home** (`henrik-home`) seeded in 079
- All existing sites (Åkarp, Danmark), users, roles, site access backfilled
- `SUPER_ADMIN` → `PLATFORM_SUPER_ADMIN` platform role + tenant membership

### Known limits / out of scope

- Dedicated DB per enterprise tenant (documented in §27, not built)
- Billing/subscription enforcement
- `energy_readings` RLS may remain disabled on Timescale columnstore (migration 082 attempts best-effort)
- Platform tenant API: DELETE + membership management at `/api/platform/tenants/{id}/members`
- Per-tenant API rate limiting via `EMIC_TENANT_API_RATE_LIMIT_PER_MINUTE` (default 600/min)
- Site-scoped RLS on all tables with `site_id` (migration 081)

### Regression

Run `.\test-windows.ps1` before deploy. Postgres RLS tests require `TEST_POSTGRES_URL`.
