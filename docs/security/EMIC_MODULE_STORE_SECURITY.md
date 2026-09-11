# EMIC Module Store Security

**Date:** 2026-09-08

---

## Boundaries preserved

| Control | State |
|---------|-------|
| `THIRD_PARTY_RUNTIME_ENABLED` | `false` in production |
| `CONTROL_ISOLATION_GATE_OPEN` | `false` (code constant) |
| COMMUNITY runtime | Denied in production |
| Store install path | Uses existing governance + staging chain |

---

## Content safety

### Server

- `store_content.sanitize_text()` strips HTML/script/event handlers
- URLs restricted to `https://` in API responses
- Oversized text truncated

### Client

- `sanitizeDisplayText()` strips tags and `javascript:` URLs before render
- No raw `dangerouslySetInnerHTML` for publisher content

### Tests

- Backend: XSS fixture module returns sanitized display name/description
- Frontend: script/onerror/javascript URL stripping unit tests

---

## API hardening

- Admin token required on all store routes
- `module_id` validated (no path traversal)
- Search max 200 chars; `page_size` max 100
- Sort whitelist only
- Preflight is non-mutating (verified by test)

---

## No bypass guarantees

Store routes do not:

- Invoke `ModuleOrchestrator` for third-party runtime
- Change trust tiers or governance policy
- Skip package validation or advisory checks
- Open control isolation gate

Install POST re-runs preflight and delegates to `ArtifactStagingService` / `PackageInstaller`.
