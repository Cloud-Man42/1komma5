# Phase 15 — Solar Forecast & Current Price Redis Cache

## Goal

Extend Redis L1/L2 caching to heavy read endpoints planned in `phase1/06_CACHE.md`.

## Deliverables

| Route | Redis key | Default TTL |
|-------|-----------|-------------|
| `GET /api/sites/{slug}/solar/forecast` | `emic:site:{id}:solar:forecast` | 1800 s |
| `GET /api/sites/{slug}/price-engine/current` | `emic:site:{id}:prices:current` | 120 s |

- Config: `SOLAR_FORECAST_REDIS_CACHE_TTL_SECONDS`, `CURRENT_PRICE_REDIS_CACHE_TTL_SECONDS`
- Cache key helpers in `energy_core.cache.service`
- API cache tests (hit on second request)
- Graceful degrade when `REDIS_URL` unset (in-memory L1 only)

## Notes

- `/solar/forecast/today` reuses cached main forecast route
- `/solar/forecast/tomorrow` still resolves live (different filter)
