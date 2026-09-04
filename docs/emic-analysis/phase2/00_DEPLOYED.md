# Phase 2 — Security & Performance Activation

**Deployed:** 2026-09-03 to `http://192.168.50.54`

## Delivered

| Item | Change |
|------|--------|
| **Admin auth (P0)** | `EMIC_ADMIN_TOKEN` Bearer required on `/api/apple-devices` when set |
| **Config UI** | Admin-token panel on `/config` (sessionStorage) |
| **Financial aggregates** | `FINANCIAL_AGGREGATES_ENABLED=true` + 365-day backfill on deploy |
| **Deploy automation** | Remote script generates admin token, runs backfill, sets Phase 1 flags |

## Operator notes

1. Read admin token from server: `grep EMIC_ADMIN_TOKEN ~/energy-monitoring/.env`
2. Paste token on `/config` → **Admin-token** panel before managing Apple devices / väggdisplay
3. Re-benchmark results: [`phase1/14_RESULTS.md`](../phase1/14_RESULTS.md)

## Next (Phase 2 backlog)

See [`phase1/16_PHASE2_RECOMMENDATIONS.md`](../phase1/16_PHASE2_RECOMMENDATIONS.md): Redis, SSE pub/sub, Pi SSE, battery optimizer.
