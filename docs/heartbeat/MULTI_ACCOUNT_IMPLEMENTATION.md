# Heartbeat Multi-Account Implementation

See also: [CURRENT_IMPLEMENTATION_ANALYSIS.md](./CURRENT_IMPLEMENTATION_ANALYSIS.md), [MULTI_ACCOUNT_USERNAME_PASSWORD.md](./MULTI_ACCOUNT_USERNAME_PASSWORD.md).

## Overview

EMIC supports multiple isolated 1Komma5 / Heartbeat accounts. Each account has its own credentials, Bearer token refresh, and circuit-breaker/cache namespace. Sites link to an account via `sites.heartbeat_account_id`.

## Data model

- `heartbeat_accounts` — credentials and connection settings per login
- `sites.heartbeat_account_id` — FK to account
- `sites.heartbeat_system_id` — preferred Heartbeat system UUID (falls back to legacy `external_system_id`)
- `sites.heartbeat_serial_number` — discovery only (serial ≠ system ID)

Migration `073_heartbeat_multi_account` copies legacy `heartbeat_settings` id=1 into account slug `default` and links sites that already have `external_system_id`.

## Backward compatibility

- Legacy admin UI (`/api/system/heartbeat-config`) still updates `heartbeat_settings` and syncs the default account.
- `HeartbeatSettingsRepository.ensure_api_token()` delegates to the default account when present.
- Åkarp keeps working via default account + existing system ID.

## Client isolation

- Token refresh locks: per account (`token_service.refresh_lock_for`)
- LKG cache keys: prefixed `acct:{id}:`
- Circuit breakers: keyed by account + API URL

## Denmark bootstrap

Set on server `.env` (never commit):

```env
HEARTBEAT_ACCOUNT_DENMARK_USERNAME=...
HEARTBEAT_ACCOUNT_DENMARK_PASSWORD=...
```

Collector startup runs `ensure_env_heartbeat_accounts()` to create/update slug `denmark` and link `summer-house-denmark` with serial `K183-600-000-021-000-P-X`.

## Admin API

- `GET /api/system/heartbeat-accounts`
- `POST /api/system/heartbeat-accounts` — name, slug, username, password only (auto-detects provider)
- `PATCH /api/system/heartbeat-accounts/{id}`
- `DELETE /api/system/heartbeat-accounts/{id}` — soft-disable when no linked sites
- `POST /api/system/heartbeat-accounts/{id}/test-connection`
- `POST /api/system/heartbeat-accounts/{id}/discover`
- `POST /api/system/heartbeat-accounts/{id}/link-site`
- `GET /api/system/heartbeat-accounts/{id}/diagnostics`
- `POST /api/system/heartbeat-accounts/{id}/discover-serial/{serial}`
- `GET /api/system/heartbeat/diagnostics` — global comparison report
