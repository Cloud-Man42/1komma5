# Phase 10 — Dashboard & Financial Redis Cache

**Deployed:** 2026-09-03 to `http://192.168.50.54`

## Goal

Extend Phase 7 tiered Redis cache to hot dashboard and financial-stats API routes per `06_CACHE.md`.

## Delivered

| Item | Change |
|------|--------|
| **Dashboard cache** | `GET /api/sites/{slug}/dashboard` — key `emic:site:{id}:dashboard`, TTL 30 s |
| **Financial cache** | `GET /api/sites/{slug}/financial-stats` — key `emic:site:{id}:financial:{period}:{year}`, TTL 300 s |
| **Config** | `DASHBOARD_REDIS_CACHE_TTL_SECONDS`, `FINANCIAL_REDIS_CACHE_TTL_SECONDS` |
| **Graceful degrade** | Memory-only when `REDIS_URL` empty |

## Key schema

| Key | TTL (L2) |
|-----|----------|
| `emic:site:{id}:dashboard` | 30 s |
| `emic:site:{id}:financial:{period}:{year\|all}` | 300 s |

## Tests

- `packages/energy-core/tests/cache/test_cache_keys.py`
- `backend/tests/test_dashboard_api.py` (Redis cache on second request)

## Next

- TimescaleDB retention policies (Phase 11)
