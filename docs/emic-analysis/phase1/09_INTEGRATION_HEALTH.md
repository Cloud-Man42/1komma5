# Integration Health

**Status:** Implemented  
**Migration:** `060_collector_tasks_integration_health` (partial — `integration_health` table)

---

## Table: `integration_health`

Composite PK: `(site_id, provider)`.

| Column | Purpose |
|--------|---------|
| `status` | `ok`, `error`, `stale` (derived at query) |
| `last_success_at`, `last_attempt_at` | Timestamps |
| `latency_ms` | Last successful call latency |
| `consecutive_failures` | Failure counter |
| `stale_seconds` | Time since last success |
| `circuit_breaker_state` | Optional breaker state |
| `last_error_class` | Truncated exception class name |

**Files:** [`alembic/versions/060_collector_tasks_integration_health.py`](../../../alembic/versions/060_collector_tasks_integration_health.py), [`db/models.py`](../../../packages/energy-core/src/energy_core/db/models.py) (`IntegrationHealthModel`).

---

## Write path (collector)

**File:** [`integrations/health.py`](../../../packages/energy-core/src/energy_core/integrations/health.py) — `IntegrationHealthRecorder`

Called from `_prefetch_live_overviews()` in fast lane ([`collector.py`](../../../collector/app/collector.py)):

- Success → `record_success(site_id, "heartbeat")`
- Missing overview → `record_failure(site_id, "heartbeat", error_class="Unavailable")`

Status `stale` derived at read when `stale_seconds > 300` and last status was `ok`.

Future providers (Mercedes, ChargeFinder, Arctic Spa) can use the same recorder.

---

## Read path (API)

**Route:** `GET /api/sites/{slug}/integration-health`

**File:** [`backend/app/api/integration_health.py`](../../../backend/app/api/integration_health.py)

Response:

```json
{
  "slug": "akarp",
  "providers": [
    {
      "provider": "heartbeat",
      "status": "ok",
      "last_success_at": "...",
      "consecutive_failures": 0,
      "stale_seconds": 0.0
    }
  ]
}
```

404 when site slug unknown. Empty `providers` for new sites with no recorded attempts.

Registered in [`backend/app/main.py`](../../../backend/app/main.py).

---

## Tests

[`backend/tests/test_integration_health_api.py`](../../../backend/tests/test_integration_health_api.py) — empty providers for new site, 404 unknown site.
