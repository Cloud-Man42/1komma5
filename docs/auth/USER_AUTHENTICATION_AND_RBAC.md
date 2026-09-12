# EMIC User Authentication & RBAC

Production-ready user authentication and role-based access control for EMIC, separate from Heartbeat/integration credentials and device (widget/display) auth.

## Overview

| Layer | Mechanism |
|-------|-----------|
| Browser sessions | HttpOnly `emic_session` cookie + CSRF double-submit (`emic_csrf` / `X-CSRF-Token`) |
| Break-glass | Optional `EMIC_ADMIN_TOKEN` Bearer → synthetic SUPER_ADMIN principal |
| Device auth | Widget/display tokens — unchanged |
| Integration auth | Heartbeat accounts, Charge Amps, Mercedes — unchanged |

## Roles

| Role | Purpose |
|------|---------|
| `SUPER_ADMIN` | All permissions (`*`), bootstrap user |
| `ADMIN` | Full admin except implicit super-only guards |
| `OPERATOR` | Read + control (battery, charging, spa, vehicles) |
| `USER` | Read-only operational data |
| `VIEWER` | Dashboard and energy read only |

Permissions are defined in `packages/energy-core/src/energy_core/auth/permissions.py` and seeded idempotently via `ensure_rbac_seed()`.

## Database Tables (migration 076)

- `emic_users` — credentials, lockout, profile
- `emic_roles`, `emic_permissions`, junction tables
- `emic_user_site_access` — site membership
- `emic_user_sessions` — server-side sessions
- `emic_auth_audit_events` — login/security events
- `admin_audit_log.actor_user_id`, `actor_type` — admin audit actor

## API Endpoints

| Endpoint | Auth |
|----------|------|
| `POST /api/auth/login` | Public (rate limited) |
| `POST /api/auth/logout` | Session + CSRF |
| `GET /api/auth/me` | Session |
| `POST /api/auth/change-password` | Session + CSRF |
| `GET /api/auth/csrf` | Session |
| `/api/admin/users`, `/api/admin/roles`, `/api/admin/auth-audit` | Permission-gated |

## Authorization Model

Routes require authentication globally when `EMIC_USER_AUTH_ENABLED=true`. Site-scoped routes additionally check:

1. Permission (e.g. `dashboard.read`, `energy.read`, `battery.control`)
2. Site membership in `emic_user_site_access` (SUPER_ADMIN / `*` bypass)

Legacy mode (`EMIC_USER_AUTH_ENABLED=false`): routes behave as before; `EMIC_ADMIN_TOKEN` gates sensitive mutations when configured.

## Environment Variables

```env
EMIC_USER_AUTH_ENABLED=true
EMIC_BOOTSTRAP_ADMIN_EMAIL=admin@example.com
EMIC_BOOTSTRAP_ADMIN_PASSWORD=          # secret, first-run only
EMIC_SESSION_TTL_HOURS=8
EMIC_LOGIN_MAX_ATTEMPTS=5
EMIC_LOGIN_LOCKOUT_MINUTES=15
EMIC_CORS_ORIGINS=https://your-domain
EMIC_COOKIE_SECURE=true
EMIC_ADMIN_TOKEN=                         # optional break-glass

# Frontend
NEXT_PUBLIC_EMIC_USER_AUTH_ENABLED=true
```

## Bootstrap

On startup, `ensure_emic_auth_bootstrap()` runs when no users exist and bootstrap env vars are set: creates SUPER_ADMIN with access to all sites.

## Frontend

- `/login` — dedicated login page
- `AuthProvider` + `useAuth()` / `can(permission)`
- Middleware redirects unauthenticated users when `NEXT_PUBLIC_EMIC_USER_AUTH_ENABLED=true`
- Admin UI: `/admin/users`, `/admin/roles`, `/admin/audit`, `/account`
- Break-glass token panel retained under config for automation migration

## Security

- Argon2 password hashing (`pwdlib[argon2]`)
- Account lockout after failed attempts
- Login rate limit per IP
- CSRF on state-changing session requests
- Security headers middleware
- Session fixation prevented (new session on login)
- Generic login error messages (no user enumeration)
- Production guard: admin token not required when user auth enabled

## Testing

```powershell
.\test-windows.ps1
```

Key test files:
- `backend/tests/test_auth_api.py`
- `backend/tests/test_route_auth_coverage.py`
- `packages/energy-core/tests/auth/`
