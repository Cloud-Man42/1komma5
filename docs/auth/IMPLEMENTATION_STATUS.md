# EMIC User Auth Implementation Status

Date: 2026-09-12

## Acceptance Criteria

| Criterion | Status | Notes |
|-----------|--------|-------|
| User DB with roles, permissions, site access | PASS | Migration 076 + models in `energy_core/db/models/users.py` |
| Email/username + password login | PASS | `POST /api/auth/login`, Argon2 hashing |
| Server-side sessions (HttpOnly cookie) | PASS | `emic_session`, sliding expiry |
| RBAC with granular permissions | PASS | ~40 permissions, 5 system roles |
| Site isolation | PASS | `emic_user_site_access`, enforced on site routes |
| Break-glass `EMIC_ADMIN_TOKEN` | PASS | Maps to SUPER_ADMIN principal |
| User/role admin API | PASS | `/api/admin/users`, `/api/admin/roles` |
| Auth audit events | PASS | `emic_auth_audit_events` + extended admin audit |
| SUPER_ADMIN protection | PASS | Cannot disable/remove last super admin |
| CSRF protection | PASS | Double-submit token on mutating session requests |
| Security headers | PASS | `SecurityHeadersMiddleware` |
| Login page + AuthProvider | PASS | `/login`, `authContext.tsx` |
| Permission-gated nav | PASS | `UserMenu`, `AppChrome` config link |
| Admin UI (users/roles/audit) | PASS | Basic list views |
| Legacy mode compatibility | PASS | `EMIC_USER_AUTH_ENABLED=false` preserves open routes |
| Widget/display unchanged | PASS | Allowlisted in route auth coverage |
| Comprehensive tests | PASS | Auth API, route coverage, datetime utils |
| Documentation | PASS | `CURRENT_AUTH_ANALYSIS.md`, this file, `USER_AUTHENTICATION_AND_RBAC.md` |

## Phased Delivery

| Phase | Status |
|-------|--------|
| 0 — Analysis | Complete |
| 1 — DB & bootstrap | Complete |
| 2 — Auth core API | Complete |
| 3 — Authorization rollout | Complete (tier A read routes + tier B/C control/admin) |
| 4 — User/role admin API | Complete |
| 5 — Frontend auth & UX | Complete (core flows; advanced user edit forms deferred) |
| 6 — Security hardening | Complete |
| 7 — Tests | Complete |
| 8 — Documentation | Complete |

## Security Review Checklist

- [x] Passwords hashed with Argon2, never returned in API
- [x] Session tokens stored hashed server-side
- [x] CSRF on cookie-authenticated mutations
- [x] Rate limiting on login
- [x] Account lockout
- [x] Site isolation enforced server-side
- [x] Permission checks authoritative in backend (UI gating is UX only)
- [x] Break-glass token optional in production when user auth enabled
- [x] Generic login failure messages
- [x] CORS configurable for production origins

## Known Limitations (Out of Scope)

- SSO/OAuth for EMIC users
- Password rotation policies (30/90 day)
- Full user create/edit wizard in frontend (API supports CRUD; UI is list-focused)
- Separate Alembic seed migration 077 (seed runs in Python bootstrap instead)

## Deploy Checklist

1. Set `EMIC_BOOTSTRAP_ADMIN_EMAIL` and `EMIC_BOOTSTRAP_ADMIN_PASSWORD` for first deploy
2. Set `EMIC_USER_AUTH_ENABLED=true` and `NEXT_PUBLIC_EMIC_USER_AUTH_ENABLED=true`
3. Configure `EMIC_CORS_ORIGINS` to production domain
4. Optionally retain `EMIC_ADMIN_TOKEN` for automation
5. Run migrations (`alembic upgrade head`)
6. Verify login at `/login` and site access for Åkarp + Danmark users
