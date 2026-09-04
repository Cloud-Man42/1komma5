# EMIC Observability

---

## 1. Current Observability Stack

| Capability | Implementation | Location |
|------------|---------------|----------|
| Request logging | Performance middleware | `performance/middleware.py` |
| Request ID | `X-Request-Id` header | Same |
| SQL query count | Per-request counter | `performance/sql_tracking.py` |
| Slow query log | ≥100ms | `sql_tracking.py` |
| In-memory metrics store | Rolling window | `performance/store.py` |
| Performance API | `GET /api/system/performance` | `backend/app/api/system.py` |
| Widget API metrics | Structured logs | `widget_auth.py` |
| ChargeFinder metrics | Cache hit rate | `chargefinder_metrics.py` |
| Price engine observability | Refresh result logging | `price_engine/observability.py` |
| Collector provider tracking | Live overview latency | `collector/site_poll_context.py` |
| Log level | `LOG_LEVEL` env | `config.py` |

**Not present:**
- Prometheus / Grafana
- OpenTelemetry / distributed tracing
- Structured JSON logging (standard)
- Correlation IDs across collector ↔ backend
- Centralized log aggregation (ELK, Loki)
- APM (Datadog, etc.)
- Alerting

---

## 2. Can EMIC Answer These Questions?

| Question | Answerable today? | How |
|----------|-------------------|-----|
| Why is dashboard slow? | ⚠️ Partial | Performance Center shows p95; per-request log with dbMs |
| Which API is slow? | ⚠️ Partial | `/system/performance` aggregates by route |
| Which API is down? | ❌ No | No health check aggregation |
| Which DB query is slow? | ⚠️ Partial | SQL log ≥100ms in server logs |
| When did data source last work? | ⚠️ Partial | Snapshot age in performance UI; provider health tables |
| Are there data gaps? | ⚠️ Partial | Heartbeat audit API; manual |
| Integration failure rate? | ❌ No | Not aggregated |
| Collector cycle duration? | ❌ No | Not measured (only logged reading count) |

---

## 3. Logging Format

Performance middleware log line (conceptual):
```
perf requestId=<uuid> totalMs=<ms> dbMs=<ms> externalMs=<ms> queries=<n> cacheHit=<bool>
```

Widget API:
```
widget_api device=<prefix> route=<path> status=<code> ms=<ms>
```

**Gap:** Collector uses standard Python logging without request correlation.

---

## 4. Data Freshness Observability

| Signal | Where |
|--------|-------|
| Snapshot `generated_at` | `site_live_snapshots`; exposed in performance center |
| Reading latest timestamp | Queryable from DB; shown in dashboard stale logic |
| `STALE_SECONDS` | Dashboard constant for live field aging |
| `WIDGET_STALE_SECONDS` | 120s default |
| Vehicle stale guard | `test_vehicle_freshness_helpers.py` |
| Spa poll state | `spa_poll_state.last_success_at` |
| Price engine state | `price_engine_state` table |
| Solar provider health | `solar_provider_health` table |

**Not surfaced in single dashboard:** Integration health overview.

---

## 5. Recommended Observability Additions

### 5.1 Structured Logging
```json
{
  "timestamp": "...",
  "level": "INFO",
  "service": "collector|backend",
  "correlation_id": "...",
  "site_slug": "akarp",
  "event": "poll_cycle_complete",
  "duration_ms": 4523,
  "readings_stored": 1,
  "snapshot_age_s": 12
}
```

### 5.2 Metrics (Prometheus-style)
- `emic_collector_cycle_duration_seconds`
- `emic_snapshot_age_seconds{site}`
- `emic_heartbeat_request_duration_seconds`
- `emic_api_request_duration_seconds{route,method}`
- `emic_db_query_duration_seconds`
- `emic_integration_up{integration}`

### 5.3 Integration Health Endpoint
`GET /api/system/integrations/health` aggregating:
- Heartbeat last success
- Charge Amps last write
- Mercedes connection state
- Spa poll state
- Weather provider health
- Snapshot age per site

### 5.4 Tracing
- OpenTelemetry on FastAPI + httpx client
- Trace ID propagated to collector logs

### 5.5 Alerting Rules
- Snapshot age > 5 min
- Collector cycle > 120s
- Heartbeat circuit open > 5 min
- Disk usage on postgres volume

---

## 6. Performance Center (Existing UI)

**Route:** `/sites/[slug]/system/performance`  
**Polls:** 10s  
**Shows:** Request counts, p95 latency, cache hit rate, snapshot age per site

**Good foundation** for operator visibility — extend with integration health.

---

## 7. Debug Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/solar/diagnostics` | Solar pipeline debug |
| `/integrations/chargefinder/diagnostics` | ChargeFinder status |
| `/vehicles/integration/diagnostics` | Mercedes health |
| `/heartbeat-audit/today` | Heartbeat data quality |
| `/system/charging-readiness` | Charge stack readiness |

These are **scattered** — no unified ops view.

---

## 8. UNKNOWN

- Production log retention period
- Whether logs are shipped to external system
- Current on-call alerting setup
