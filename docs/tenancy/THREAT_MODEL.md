# EMIC Multi-Tenant Threat Model

## Scope

Logical tenant isolation in a shared EMIC deployment: one application instance, one PostgreSQL database, multiple customers (tenants) with strict data separation.

## Assets

| Asset | Sensitivity |
|-------|-------------|
| Energy readings / snapshots | High — customer operational data |
| Integration credentials (Heartbeat, ChargeAmps, Mercedes) | Critical |
| User accounts / sessions | High |
| Audit logs | High |
| Economy / financial data | High |
| Vehicle / charging / SPA control | High — physical impact |
| Platform marketplace artifacts | Medium — shared catalog |

## Threat Actors

1. **Malicious tenant user** — member of Tenant A attempting access to Tenant B
2. **Compromised session** — stolen cookie used across tenant boundaries
3. **Insider tenant admin** — escalation to platform or other tenants
4. **Platform support abuse** — over-broad cross-tenant access
5. **External attacker** — IDOR, tenant ID spoofing, device token abuse

## Threats and Mitigations

### T1: Tenant ID Spoofing

**Description:** Client sends `tenantId` in header, query, or body to access another tenant.

**Impact:** Full cross-tenant data access.

**Mitigation:**
- `TenantContext` derived from session + membership validation
- Ignore or verify client-supplied tenant identifiers
- Creates set `tenant_id` from server context only
- RLS enforces `app.current_tenant_id` at DB layer

### T2: Insecure Direct Object Reference (IDOR)

**Description:** Attacker uses known `siteId`, `userId`, `integrationId` from Tenant B while authenticated in Tenant A.

**Impact:** Read/modify/delete other tenant resources.

**Mitigation:**
- Every resource access: `resource.tenant_id == CurrentTenantId`
- Site slug routes require membership + tenant match
- Cross-tenant IDOR test suite (25+ cases)
- RLS blocks SELECT/INSERT/UPDATE/DELETE across tenants

### T3: Missing TenantId in Application Query

**Description:** Developer forgets `WHERE tenant_id = ?` in repository or raw SQL.

**Impact:** Returns or modifies wrong tenant data.

**Mitigation:**
- Tenant-scoped repository methods (`list_for_tenant`)
- PostgreSQL RLS as defense-in-depth
- Code review + architecture tests for `list_all()` without scope
- Global query filters where practical (SQLAlchemy)

### T4: Cache Leakage

**Description:** Shared Redis key `site:{id}:snapshot` reused across tenants if site IDs collide or keys omit tenant.

**Impact:** Stale or wrong tenant data served.

**Mitigation:**
- Prefix all keys: `tenant:{tenantId}:site:{siteId}:...`
- Clear tenant-scoped frontend state on switch
- Test cache isolation

### T5: Connection Pool RLS Leakage

**Description:** `app.current_tenant_id` set on connection A persists when connection returned to pool and reused for Tenant B request.

**Impact:** Tenant B request sees Tenant A data via RLS wrong context.

**Mitigation:**
- Use `SET LOCAL` (transaction-scoped) via `set_config(..., true)`
- Reset session variables on pool checkout/checkin
- Dedicated integration test: alternating tenants on same pool

### T6: Background Job Cross-Tenant Processing

**Description:** Collector runs `list_all()` and writes data without tenant boundary.

**Impact:** Job logic mixes tenants; failure cascades.

**Mitigation:**
- Per-tenant job loops with explicit `TenantContext`
- Tenant-scoped locks: `tenant:{id}:heartbeat-sync`
- Disabled tenant skipped

### T7: Realtime Subscription Leakage

**Description:** SSE/WebSocket group allows subscribe without tenant membership check.

**Impact:** Live data stream from other tenant.

**Mitigation:**
- Groups: `tenant:{tenantId}:site:{siteId}`
- Validate membership before subscribe
- Device tokens bound to allowed site IDs within tenant

### T8: Export / Report Leakage

**Description:** Download endpoint serves file without tenant verification.

**Impact:** Data exfiltration.

**Mitigation:**
- All exports tagged with `tenant_id`
- Download verifies `export.tenant_id == CurrentTenantId`
- Client CSV inherits scoped API responses

### T9: Secret / Credential Leakage

**Description:** Integration credentials stored or retrieved without tenant namespace.

**Impact:** Cross-tenant credential access.

**Mitigation:**
- Secret path: `tenant/{tenantId}/heartbeat/{accountId}`
- Heartbeat accounts have `tenant_id` FK
- Support mode never returns decrypted secrets

### T10: Platform Admin Abuse

**Description:** Platform admin uses cross-tenant access without audit or beyond need.

**Impact:** Mass data exposure.

**Mitigation:**
- Explicit elevated code paths only
- All bypass audited in `emic_auth_audit_events`
- App DB user without BYPASSRLS
- Separate platform admin UI

### T11: Support Access Abuse

**Description:** PLATFORM_SUPPORT views tenant data without customer visibility or audit.

**Impact:** Unauthorized support snooping.

**Mitigation:**
- Explicit support mode flag in UI
- Audit event on support tenant entry
- Minimal permissions; no secret decryption

### T12: User Switch State Leakage

**Description:** User A logs out; User B logs in; cached tenant/site data from A visible to B.

**Impact:** Session confusion, data leak.

**Mitigation:**
- Clear localStorage/sessionStorage tenant keys on logout
- Clear in-memory React state
- Server session invalidated; new tenant context on login

### T13: RLS Bypass

**Description:** Application uses superuser role or `BYPASSRLS` for normal queries.

**Impact:** RLS provides no protection.

**Mitigation:**
- Application role without BYPASSRLS
- Platform elevation via separate audited path
- Migration documents role permissions

### T14: Cross-Tenant Relation Creation

**Description:** `UserSiteAccess` links user in Tenant A to site in Tenant B.

**Impact:** Persistent unauthorized access.

**Mitigation:**
- DB CHECK or composite FK enforcing same tenant
- Application validation before insert
- Migration validation script

## Residual Risks

| Risk | Acceptance |
|------|------------|
| Platform-global marketplace catalog | Shared read-only; no tenant secrets |
| Geo chargefinder cache | Read-only POI data |
| SQLite dev/test without RLS | App-layer enforcement; Postgres RLS tested separately |
| Dedicated DB per enterprise | Out of scope; architecture allows future split |

## Test Coverage Requirements

See `backend/tests/test_tenant_security.py` and `test_tenant_rls.py` for enforcement of T1–T14.
