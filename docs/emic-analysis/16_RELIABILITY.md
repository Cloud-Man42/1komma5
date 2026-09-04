# EMIC Reliability

---

## 1. Design Principle

EMIC should **never crash** because an integration is down. Assessment based on code patterns.

---

## 2. Failure Scenario Matrix

| Failure | EMIC behavior | Circuit breaker | LKG fallback | User impact |
|---------|---------------|-----------------|--------------|-------------|
| **Nord Pool / Heartbeat prices** | Price engine logs error; uses fallback purchase/export prices | Heartbeat CB | Fallback site prices | Estimated economics |
| **Heartbeat readings** | Skip degraded readings; conditional upsert preserves fields | ✅ CB + LKG | Last DB readings | Stale live data |
| **Heartbeat live overview** | Collector continues; enrichment uses stale/missing overview | ✅ resilient_call | LKG store | EV accounting may skip |
| **Mercedes** | Supervisor backoff 900s; stale guard on vehicle state | ✅ auth CB (5 failures) | LKG merge in repo | Vehicle dashboard stale |
| **SMHI/DMI/Open-Meteo** | Solar forecast degraded mode | Provider health tracked | `_degraded_from_last_good` | Reduced forecast accuracy |
| **Charge Amps** | Smart charging cycle logs exception; continues | Client retries (3×) | Last charger state in DB | Charging not optimized |
| **Arctic Spa** | Spa poll error logged; spa features unavailable | 429/503 retry | Last consumer sample | Spa section stale |
| **ChargeFinder** | Circuit breaker 900s cooldown | ✅ dedicated CB | 7-day geohash cache | Admin lookup fails |
| **Modbus** | N/A — removed | — | — | — |
| **Database down** | API returns 500; collector logs exception | — | — | Full outage |
| **Collector down** | Snapshots age; no new readings | — | Last snapshot in DB | Progressive staleness |
| **Backend down** | Frontend/Pi error states | — | Pi client state only | No data refresh |
| **Caddy down** | Complete service unreachable | — | — | Full outage |

---

## 3. Resilience Patterns in Code

### 3.1 Circuit Breaker
**File:** `providers/resilience.py`
- Threshold: 3 failures
- Cooldown: 60s
- Used by: Heartbeat client, ChargeFinder

### 3.2 Last-Known-Good
**File:** `providers/resilience.py` — `LastKnownGoodStore`
- Per-key with max_age
- Used with `resilient_call()` wrapper

### 3.3 Retry
| Integration | Retry pattern |
|-------------|---------------|
| Heartbeat | 401 refresh; 5xx retry on readings |
| Charge Amps | Max 3 retries, 20s timeout |
| Arctic Spa | 3 retries on 429/503, exponential backoff |
| Mercedes | Exponential backoff on auth; WS reconnect |

### 3.4 Timeouts
| Integration | Timeout |
|-------------|---------|
| Heartbeat | 20s |
| Charge Amps | 20s |
| Weather providers | 30s |
| ChargeFinder | 15s |
| Arctic Spa | 10s |

### 3.5 Error Isolation
- Collector enrichment wrapped in try/except per phase
- Smart charging separate try block from enrichment
- Virtual bridge separate try block
- Degraded readings skipped, not zero-filled

---

## 4. Gaps Requiring Circuit Breakers

| Gap | Risk | Recommendation |
|-----|------|----------------|
| Solar forecast weather fetch | Blocks collector cycle up to 30s×providers | Per-provider timeout + parallel + skip |
| `list_financial_stats` no timeout | Large date ranges hang request | Query timeout + pre-aggregation |
| SSE infinite loop | DB connection held per client | Connection limits + idle timeout |
| Apple device registration open | Abuse | Auth + rate limit |
| No bulkhead isolation | Slow solar blocks snapshot write | Separate asyncio tasks with priorities |

---

## 5. Cascading Failure Analysis

```
Slow Heartbeat (20s timeout)
  → Collector cycle extends beyond poll interval
  → Snapshots delayed
  → All dashboards show increasing stale age
  → Smart charging uses stale EnergyState
  → NOT a crash — degraded operation
```

```
Mercedes auth failure
  → 900s backoff
  → Vehicle SOC unavailable
  → Smart charging continues with charger-only data
  → NOT a crash
```

```
Database connection exhaustion (SSE + polls)
  → API 500 errors
  → Potential crash under load — **risk at scale**
```

---

## 6. Retry Storm Prevention

| Mechanism | Status |
|-----------|--------|
| ChargeFinder 900s cooldown | ✅ |
| Mercedes 900s auth backoff | ✅ |
| Heartbeat circuit breaker 60s | ✅ |
| Frontend Pi exponential backoff | ✅ |
| Frontend dashboard fixed interval (no backoff on success) | ⚠️ Constant load |
| Collector retry on same cycle | ⚠️ No delay between steps |

**Missing:** Jitter on collector retry; exponential backoff on Heartbeat 5xx.

---

## 7. Bulkhead Recommendations

| Bulkhead | Isolate |
|----------|---------|
| Ingestion task | Heartbeat readings (critical) |
| Enrichment task | Solar, spa, vehicle (best-effort) |
| Control task | Smart charging writes (time-sensitive) |
| API read pool | Separate from collector write pool |

Current: Single collector asyncio loop — **no bulkheads**.

---

## 8. Data Integrity Under Failure

**Phase 3 fixes (health report):**
- Conditional upsert — don't overwrite good fields with nulls
- `present_fields` tracking on raw readings
- EV accounting skips zero-fill without live overview
- Empty Heartbeat payloads not cached

These prevent **corrupt data** during outages — stronger than crash prevention.

---

## 9. Recommended Reliability Roadmap

1. Add Heartbeat health to overview UI (data exists in audit/readiness)
2. Collector cycle timing metrics + alert if cycle > 2× interval
3. SSE connection limits
4. Redis-backed LKG shared across workers
5. Bulkhead collector tasks
6. Pi offline LKG persistence
7. Graceful degradation mode flag on API responses (`degraded: true`)

---

## 10. UNKNOWN

- Production incident history
- Actual MTTR for Heartbeat outages
- Database connection pool size configuration
