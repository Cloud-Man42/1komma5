# Phase 7 — Optional Redis Cache Layer

**Deployed:** 2026-09-03 to `http://192.168.50.54`

## Delivered

| Item | Change |
|------|--------|
| **Tiered cache** | L1 in-memory + optional L2 Redis when `REDIS_URL` is set |
| **Write-through** | Collector `SnapshotWriter` populates Redis after DB upsert |
| **Graceful degrade** | Redis connection failures fall back to memory-only |
| **Docker** | `redis:7-alpine` service; default `REDIS_URL=redis://redis:6379/0` in compose |
| **Observability** | Performance Center shows cache backend + Redis availability |

## Configuration

| Env | Default | Purpose |
|-----|---------|---------|
| `REDIS_URL` | empty (dev); `redis://redis:6379/0` in docker-compose | Enable L2 cache |
| `SNAPSHOT_REDIS_CACHE_TTL_SECONDS` | 60 | Redis TTL for site snapshots |

## Key schema

| Key | Value | TTL |
|-----|-------|-----|
| `emic:site:{site_id}:snapshot` | JSON site live snapshot | 60 s (L2) / 5 s (L1 API read) |

## Next

- SSE pub/sub via Redis (replace 1 s DB poll in live-stream)
- Dashboard/financial Redis keys per `06_CACHE.md`
