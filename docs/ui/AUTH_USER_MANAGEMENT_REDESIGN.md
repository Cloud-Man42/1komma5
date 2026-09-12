# EMIC Auth & Admin UI Redesign

## Previous problems

- Login page used undefined CSS, showed full AppChrome header, and ignored `?next=` redirects.
- Admin users/roles/audit pages were read-only tables without search, filters, or CRUD flows.
- Account page used inline password form without modal UX or live policy validation.
- No shared admin component library or dedicated stylesheet.

## Design goals

- Reuse EMIC design tokens and config-hub visual patterns.
- Provide Swedish UI copy and dark/light theming via `[data-theme]`.
- Gate all actions with `can(permission)` checks; backend remains authoritative.
- Do not surface features unsupported by the API.

## Component inventory

| Component | Location |
|-----------|----------|
| Admin UI primitives | `frontend/src/components/admin-ui/` |
| Admin shell | `frontend/src/components/admin/AdminShell.tsx` |
| User editor | `frontend/src/components/admin/UserEditorForm.tsx` |
| Role editor | `frontend/src/components/admin/RoleEditorForm.tsx` |
| Login hero | `frontend/src/components/auth/LoginHero.tsx` |
| Stylesheet | `frontend/src/styles/admin-auth.css` |
| API client | `frontend/src/lib/adminUsersApi.ts` |

## Features intentionally omitted

- Remember me, forgot password, avatar upload
- Active sessions list, failed-attempt counter, manual unlock
- Self-service profile edit, delete user
- “Last successful login” on account (API only tracks last login attempt)

## Responsive & accessibility

- Tables collapse to card lists below 900px.
- Modals trap focus and close on Escape.
- Status badges and form errors use `role="alert"` / `role="status"`.
- Login labels remain visible; username field autofocuses.

## QA checklist

| Area | Status |
|------|--------|
| Login split layout + `?next=` | PASS |
| Admin shell navigation | PASS |
| Users list filters/summary | PASS |
| User create/edit + reset password | PASS |
| Roles list/create/edit/duplicate/delete | PASS |
| Account + change password modal | PASS |
| Audit filters + expandable rows | PASS |
| Toast feedback | PASS |
| Vitest coverage | PASS |
| Backend unchanged except site-options | PASS |
