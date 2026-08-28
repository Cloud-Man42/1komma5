# EMIC Performance Baseline

Measured with `scripts/performance-baseline.ps1` against the production-like stack.

## Performance budget (targets)

| Metric | Target |
|--------|--------|
| Snapshot/summary API p50 | < 50 ms (cache hit), < 150 ms (DB read) |
| Normal API p50 / p95 | < 150 ms / < 400 ms |
| Dashboard summary server | < 200 ms |
| History (24h, bucketed) | < 500 ms |
| Cache hit rate (L1 summary) | > 80% after phase 2 |

## Top slow operations (fill after baseline run)

| Rank | Route / operation | p50 ms | p95 ms | Notes |
|------|-------------------|--------|--------|-------|
| 1 | _pending measurement_ | — | — | Run `.\scripts\performance-baseline.ps1` |
| 2 | | | | |
| 3 | | | | |

## Hypothesized bottlenecks (pre-measurement)

1. Dashboard live Heartbeat price fetch — **mitigated**: prices now read from `market_prices` DB
2. Solar observation evaluation on GET — **mitigated**: moved to collector cycle
3. `/readings` ad-hoc aggregation — **mitigated**: Timescale CAGG path when `ENABLE_TIMESCALEDB=true`
4. Collector 4× Heartbeat overview per site — **mitigated**: `SitePollContext`
5. Frontend duplicate `/dashboard` fetches — **mitigated**: `SiteDataProvider` in site layout
6. Process-local cache — L1 `InMemoryCacheService` with single-flight

## How to re-run

```powershell
.\scripts\performance-baseline.ps1 -BaseUrl http://localhost:8000 -Site akarp
```

Results are written to `docs/performance/baseline-results.json`.
