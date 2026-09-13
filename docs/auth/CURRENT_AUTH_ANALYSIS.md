# EMIC Current Authentication Analysis

## Tech stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI (Python 3.12+), SQLAlchemy 2 async |
| Frontend | Next.js App Router, React |
| Proxy | Caddy — same-origin `/api/*` + frontend |
| Database | SQLite (dev/test), PostgreSQL/TimescaleDB (prod) |

## Current authentication

### 1. Shared admin Bearer token (primary)

- Env: `EMIC_ADMIN_TOKEN`
- Dependency: `backend/app/admin_auth.py` → `require_admin_token`
- Applied router-wide in `backend/app/main.py` on ~35 `/api` routers
- Dev/test: empty token → routes are **open** (no auth)
- Production: startup guard requires token (`assert_emic_admin_token_production_safe`)

### 2. Device tokens (widget / display)

- Table: `apple_devices` (token_prefix + token_hash + scopes)
- Widget: Bearer + `widget.read` scope
- Display: Bearer or HttpOnly cookie from enroll URL
- **Unchanged** by user auth work — separate client identity model

### 3. Integration credentials (NOT EMIC users)

- `heartbeat_accounts`, `heartbeat_settings`, `vehicle_provider_connections`
- Fernet-encrypted passwords/tokens for external APIs
- Completely separate from EMIC application login

### 4. Module runtime authorization

- `runtime_pilot_authorizations`, isolated runtime permissions
- Module capability sandbox — not human user RBAC

## Current authorization

- **Binary**: admin (valid token) vs anonymous (401/403) vs open (dev)
- No roles, permissions, or site-level user access
- Device tokens scoped to `default_site_slug` only

## Current user storage

**None.** No `users` table. No password hashing for humans.

## Frontend auth

- Token in `localStorage` key `emic_admin_token`
- `AdminAuthPrompt` overlay on 401/403
- No login page, no middleware, no route guards
- `adminFetch` sends `Authorization: Bearer`

## Audit logging

- Table: `admin_audit_log` (migration 061)
- Records action, path, resource — **no actor identity**
- Opt-in per mutation route (~15 modules)

## Security weaknesses

| Issue | Risk |
|-------|------|
| Shared admin token | No per-user accountability; token leak = full access |
| localStorage token | XSS can exfiltrate token |
| Dev open mode | Empty token disables all protection |
| No CSRF | Bearer in header mitigates; cookie sessions need CSRF |
| No login rate limit | Admin API unprotected from brute force |
| No actor in audit | Cannot attribute changes to individuals |
| SEMP unauthenticated | Protocol requirement; network exposure risk |
| Display enroll URL | One-time token in query string |

## Recommended migration

1. Add EMIC user database with Argon2 password hashing
2. HttpOnly session cookies for browser users
3. RBAC + granular permissions + site access
4. Keep `EMIC_ADMIN_TOKEN` as optional break-glass (SUPER_ADMIN)
5. Feature flag `EMIC_USER_AUTH_ENABLED` for phased rollout
6. Extend audit with `actor_user_id`
7. Frontend login page replaces token overlay when auth enabled

## Backward compatibility

| Component | Strategy |
|-----------|----------|
| `EMIC_ADMIN_TOKEN` | Retained as break-glass SUPER_ADMIN |
| Widget/display | Unchanged |
| Heartbeat credentials | Unchanged, separate tables |
| Dev/tests | `EMIC_USER_AUTH_ENABLED=false` preserves open routes |
| Existing API clients | Break-glass Bearer continues to work |

## Risks during migration

- Breaking automation scripts that rely on admin token only → document break-glass
- Partial permission rollout leaving endpoints over/under protected → tiered migration + route coverage tests
- Session cookies behind Caddy → ensure `Secure`, `ProxyHeadersMiddleware`, correct SameSite
