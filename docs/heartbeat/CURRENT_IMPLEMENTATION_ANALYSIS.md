# Heartbeat / 1KOMMA5 — Current Implementation Analysis

## Overview

EMIC is transitioning from a single global Heartbeat configuration (`heartbeat_settings` id=1) to **multi-account username/password** with per-site binding. Core backend plumbing exists (migrations 073/074, account repo, client factory, collector). Remaining work focuses on UX simplification, provider-dispatched discovery, and closing single-account leaks.

## Current auth flow

### 1Komma5 backend (Åkarp / default)

1. Admin stores username + encrypted password in `heartbeat_accounts`.
2. `HeartbeatAccountRepository.ensure_api_token()` calls `fetch_bearer_token()` via external `onekommafive.Client`.
3. JWT `exp` checked; refresh when within 300s of expiry.
4. `HeartbeatClient` sends `Authorization: Bearer {token}` to `heartbeat.1komma5grad.com/api`.
5. On HTTP 401: one refresh via callback → retry once.

**No cookies or browser session.**

### GridX backend (my.1komma5.io / api.gridx.de)

1. Same credential storage.
2. Auth0 **password-realm** grant → access + refresh tokens.
3. Refresh via standard OAuth refresh_token grant.
4. `GridXClient` calls `api.gridx.de` with Bearer token.
5. On HTTP 401: refresh once → retry once.

**No cookies.**

### Token persistence

- Encrypted at rest: `encrypted_password`, `encrypted_api_token`, `encrypted_refresh_token`
- Per-account `asyncio.Lock` via `token_service.refresh_lock_for(account_id)`
- No global mutable auth singleton

## Account model

| Table / field | Purpose |
|---------------|---------|
| `heartbeat_accounts` | Per-login credentials, provider, connection, auth audit |
| `sites.heartbeat_account_id` | FK to account |
| `sites.heartbeat_system_id` | External system UUID |
| `sites.heartbeat_gateway_id` | GridX gateway UUID |
| `sites.heartbeat_serial_number` | Discovery / matching |
| `heartbeat_settings` (id=1) | Legacy singleton; poll intervals; syncs default account |

## API client design

```
client_factory.create_heartbeat_client(session, account_id)
  → provider == gridx  → GridXClient
  → provider == 1komma5 → HeartbeatClient
```

Collector uses `create_heartbeat_clients_by_account()` + `SitePollContext.client_for_site(site)`.

## Site mapping

Resolution order for system ID: `site.heartbeat_system_id` → `site.external_system_id`.

Account resolution: `site.heartbeat_account_id` → slug `default`.

## Caching

- LKG cache keys prefixed `acct:{accountId}:`
- Circuit breakers keyed by account + API URL
- **Gap:** separate LKG stores in `client.py` vs `gridx_client.py`

## Background jobs

Collector fast lane: per-site provider bindings, isolated auth failures (Danmark failure does not stop Åkarp).

## Single-account assumptions (remaining)

| Location | Issue |
|----------|-------|
| `create_heartbeat_client(session)` without account_id | Falls back to default |
| `ev_chargers.py` EV sync | Uses default client |
| `energy/client_access.py` | Default account only |
| Bridge / write-test services | Default client |
| Price engine | `fetch_market_prices` missing on GridXClient |
| `SitePollContext.from_clients` | Arbitrary default_client fallback |
| Legacy `HeartbeatConfigPanel` | Single-account UI with token field |
| `account_bootstrap.py` | Hardcoded Denmark UUIDs |
| Serial discovery | 1komma5 list paths only |

## Risk areas

1. **Provider auto-detection** — must not assign wrong backend on ambiguous failures
2. **GridX discovery** — API shape must be verified live, not guessed
3. **Legacy Åkarp** — default account migration must remain intact
4. **Price engine** — Denmark market prices fail without GridX tariff adapter
5. **EV bridge** — 1komma5-only; OK for Åkarp scope

## Migration plan (incremental)

1. **075** — `last_api_call_at`, `last_successful_api_call_at` on accounts
2. **auth_probe** — auto-detect provider on create/update/test
3. **discovery_service** — provider-dispatched full discovery + serial match
4. **API** — test-connection, discover, global diagnostics, simplified schemas
5. **UI merge** — single Heartbeat Accounts panel
6. **Leak fixes** — site-aware clients, GridX price alias
7. **Tests + docs** — full regression

## Verified API differences

| | Åkarp (default) | GridX accounts |
|--|-----------------|----------------|
| Auth | onekommafive SDK | Auth0 password-realm |
| API | heartbeat.1komma5grad.com/api | api.gridx.de |
| Live | /v3/systems/{id}/live-overview | /systems/{id}/live |
| Same API server | **NO** | |
| Same auth mechanism | **NO** | |
| Separate account context | **YES** | |

See also: [MULTI_ACCOUNT_IMPLEMENTATION.md](./MULTI_ACCOUNT_IMPLEMENTATION.md), [MULTI_ACCOUNT_USERNAME_PASSWORD.md](./MULTI_ACCOUNT_USERNAME_PASSWORD.md).
