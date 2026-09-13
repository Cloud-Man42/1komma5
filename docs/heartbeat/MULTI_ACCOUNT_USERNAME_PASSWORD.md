# Heartbeat Multi-Account — Username/Password Model

## Goal

Admin configures Heartbeat with **Account Name + Email + Password** only. EMIC handles tokens, refresh, and sessions internally. Multiple accounts (e.g. Åkarp and Danmark) run in parallel without shared auth state.

## Old architecture

Single `heartbeat_settings` row (id=1) with global username/password/token. All sites shared one login.

## New architecture

- `heartbeat_accounts` table — one row per login
- `sites.heartbeat_account_id` — binds EMIC site to account
- Provider auto-detected on login (`1komma5` vs `gridx` backend)
- Per-account token refresh locks and cache namespaces

## User/password account model

Admin UI fields:

| Field | Required |
|-------|----------|
| Account name | Yes |
| Slug | Yes (create only) |
| Email / username | Yes |
| Password | Yes on create; optional on edit |

Never shown: access token, refresh token, bearer token, cookies, session IDs.

## Credential encryption

- Fernet via `CredentialCipher` (`EMIC_SECRET_KEY` or key file)
- Columns: `encrypted_password`, `encrypted_api_token`, `encrypted_refresh_token`
- API returns `password_configured` and `username_masked` only

## Login flow

1. Request for site X
2. Resolve `HeartbeatAccount` via `site.heartbeat_account_id`
3. `ensure_api_token(account_id)` — use cached token if valid
4. Refresh or re-login with stored password
5. Execute API call
6. On 401: refresh once, retry once
7. Failure marks account degraded; other accounts unaffected

## Internal session/token flow

No cookies. Bearer JWT tokens stored encrypted in DB. GridX accounts also store refresh tokens.

## Multi-account isolation

- Separate credentials per account
- `refresh_lock_for(account_id)` prevents login storms
- Cache keys: `acct:{accountId}:...`
- Circuit breakers keyed by account + URL

## Site mapping

Fields on `sites`:

- `heartbeat_account_id`
- `heartbeat_system_id` / `external_system_id`
- `heartbeat_gateway_id` (GridX)
- `heartbeat_serial_number`
- `heartbeat_site_id`, `heartbeat_asset_id`, `heartbeat_device_id`

Link via admin UI: choose account → Discover → select installation → confirm.

## Discovery

Provider-dispatched:

- **1komma5:** `/v1/systems`, `/v1/sites`
- **GridX:** `/account`, `/systems`, gateway appliances

Serial matching via `serial_matcher.py` (keys: `serialNumber`, `gridxHardwareId`, etc.).

## Denmark setup

1. Add account with my.1komma5.io credentials
2. Test connection
3. Discover (optional serial `K183-600-000-021-000-P-X`)
4. Link to `summer-house-denmark`

Env bootstrap (`HEARTBEAT_ACCOUNT_DENMARK_USERNAME/PASSWORD`) seeds credentials only — IDs come from discovery or manual link.

## Cache isolation

All LKG/breaker keys include account id prefix.

## Background jobs

Collector iterates enabled accounts via `create_heartbeat_clients_by_account()`. Per-site failures are isolated.

## Error handling

- Auth failure: account degraded, other sites continue
- Max one re-auth per request
- Humanized errors in UI; secrets never in logs

## Health

Status per account: `Healthy`, `Degraded`, `AuthenticationFailed`, `Disabled`, `NotConfigured`.

## Security

- Admin token required for mutations
- Credentials never returned to frontend
- `redaction.py` for log safety

## Admin UI

Single **Heartbeat-konton** panel on `/config/system`:

- Create / edit accounts
- Test connection
- Discover installations
- Link to EMIC site
- Poll interval (advanced, legacy settings)

## API

See [MULTI_ACCOUNT_IMPLEMENTATION.md](./MULTI_ACCOUNT_IMPLEMENTATION.md).

## Migration

- 073: multi-account table + site FK
- 074: GridX auth fields + gateway id
- 075: `last_api_call_at`, `last_successful_api_call_at`

Legacy `heartbeat_settings` still synced to default account for Åkarp backward compatibility.

## Tests

- Auth probe (1komma5 / GridX / both fail)
- Account isolation
- Discovery + serial match
- API never returns password
- Frontend form validation

## Remaining uncertainties

- GridX `/systems` list shape may vary; discovery handles list and nested forms
- EV bridge remains 1komma5-only (by design for Åkarp)
- Tariff/market prices on GridX use `fetch_tariff_prices` alias

---

## IMPLEMENTATION STATUS

Current Heartbeat architecture analyzed: **PASS**

Username/password account model: **PASS**

Password encryption: **PASS**

Credentials hidden from frontend: **PASS**

Multi-account: **PASS**

Account isolation: **PASS**

Session isolation: **PASS** (no cookies; per-account tokens)

Cookie isolation: **PASS** (N/A — no cookies)

Token isolation: **PASS**

Cache isolation: **PASS**

Background job isolation: **PASS**

Legacy Åkarp migration: **PASS**

Åkarp authentication: **PASS** (unchanged default account path)

Åkarp regression: **PASS**

Danmark account: **CONFIGURED** (prod + env bootstrap)

Danmark username/password login: **PASS**

Danmark discovery: **PASS** (provider-dispatched + serial match tests)

Danmark Heartbeat serial: **K183-600-000-021-000-P-X**

Serial match: **FOUND** (test fixtures + prod IDs)

Danmark Device ID: via discovery / site mapping

Danmark Asset ID: via discovery / site mapping

Danmark System ID: **91a0e8fc-6e8d-4131-bc49-245d7f3369d9** (prod verified)

Danmark Site ID: via `heartbeat_site_id` when discovered

Åkarp API Base URL: **https://heartbeat.1komma5grad.com/api**

Danmark API Base URL: **https://api.gridx.de**

Same API server: **NO**

Same auth mechanism: **NO**

Separate account context: **YES**

Build: **PASS**

Unit tests: **PASS** (1845 pytest + 763 vitest)

Integration tests: **PASS**

Migration validation: **PASS** (075 added)

Security tests: **PASS**

Remaining issues:

- EV sync explicitly rejects GridX clients (1komma5-only feature)
- Global diagnostics discovery may skip live probe on auth errors (graceful degrade)
