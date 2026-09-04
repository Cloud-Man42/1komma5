# TOP 30 Performance Improvements

Prioritized by **impact / effort** (highest ratio first).

| # | Impact | Effort | Item | File/Area | Expected gain |
|---|--------|--------|------|-----------|---------------|
| 1 | CRITICAL | M | Solar forecast snapshot GET | `solar_forecast.py`, collector | p95 34s → <200ms under load |
| 2 | HIGH | M | Pre-aggregate financial stats | `repositories.py`, collector | Economy API 10× faster |
| 3 | HIGH | M | Redis shared snapshot cache | `cache/service.py` | Multi-worker cache hits |
| 4 | HIGH | S | Remove duplicate dashboard polls | `SiteDataProvider`, overview page | 50% fewer dashboard calls |
| 5 | HIGH | M | SSE push via pub/sub | `snapshot.py`, collector | Eliminate 1 QPS/client DB poll |
| 6 | HIGH | M | Collector prioritized sub-loops | `collector.py` | Faster snapshot freshness |
| 7 | HIGH | S | Pi poll 4s → 8s | `usePiDashboardData.ts` | 50% fewer display API calls |
| 8 | MEDIUM | S | Energy dashboard use config refresh | `useEnergyDashboardData.ts` | Consistent load |
| 9 | MEDIUM | M | Display overview from snapshot | `display_service.py` | Single DB read for Pi |
| 10 | MEDIUM | M | Incremental snapshot writer | `snapshots/writer.py` | Shorter collector cycle |
| 11 | MEDIUM | S | ETag on snapshot endpoint | `snapshot.py` | Browser conditional GET |
| 12 | MEDIUM | S | `cache: no-store` → selective | `api.ts` | HTTP cache for static snapshots |
| 13 | MEDIUM | M | Parallel Heartbeat price refresh | `collector._collect_market_prices` | Shorter enrichment |
| 14 | MEDIUM | M | Parallel weather provider fetch | solar intelligence providers | Avoid 30s×N sequential |
| 15 | MEDIUM | S | Memoize Recharts data | Overview/Energy components | Less client CPU |
| 16 | MEDIUM | M | Timescale CAGG for all chart paths | `repositories.py` | Faster readings API |
| 17 | MEDIUM | M | Timescale retention/compression | migrations | Sustained query speed |
| 18 | MEDIUM | L | Unified frontend SSE subscription | All dashboard hooks | Replace N polls with 1 stream |
| 19 | LOW | S | Sidebar price 300s → align with config | `DashboardSidebar.tsx` | Minor |
| 20 | LOW | M | Vehicle list query batching | `vehicles.py` | Fewer DB round-trips |
| 21 | LOW | S | Dynamic import more chart panels | Energy/Solar overviews | Smaller initial bundle |
| 22 | LOW | M | Route-level CSS splitting | `layout.tsx` | Faster Pi first paint |
| 23 | LOW | M | DB connection pool tuning | `session.py` | UNKNOWN baseline needed |
| 24 | LOW | S | Skip overview extra fetch when layout has solar | `useOverviewData.ts` | Fewer calls |
| 25 | LOW | M | Materialized daily peaks | peaks API | Faster peak queries |
| 26 | LOW | S | Production perf debug dedup | `api.ts` | Catch duplicate fetches |
| 27 | LOW | M | Snapshot JSON compression | `site_live_snapshots` | Storage + IO |
| 28 | LOW | L | Read replica for dashboards | infrastructure | Scale reads |
| 29 | LOW | M | next/image for any photos | frontend | Minor bandwidth |
| 30 | LOW | S | Increase SSE poll to 2–3s if keeping DB poll | `snapshot.py` | 50% less SSE DB load |

---

## Measurement

Re-run after changes:
```powershell
.\scripts\performance-baseline.ps1 -BaseUrl http://192.168.50.54 -Site akarp
```

Compare against `docs/performance/baseline-results.json`.

---

## Quick Wins (< 1 week, high impact)

1. Duplicate dashboard poll fix (#4)
2. Pi poll interval (#7)
3. ETag on snapshot (#11)
4. Economy pre-aggregation start (#2 partial — daily rollup)

---

## Critical Path

Items #1 (solar snapshot) and #2 (financial pre-agg) unblock scalability for multi-user and multi-year data.
