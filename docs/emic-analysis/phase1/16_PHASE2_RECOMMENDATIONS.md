# Phase 2 Recommendations

Prioritised follow-ups after Phase 1 deploy and re-benchmark ([`14_RESULTS.md`](14_RESULTS.md)).

---

## P0 — Security

1. **Auth on `/api/apple-devices`** — require `EMIC_ADMIN_TOKEN` Bearer or Caddy basic auth ([`10_SECURITY.md`](10_SECURITY.md)).
2. **Audit admin mutations** — site config, vehicle commands, spa control.

---

## P1 — Performance activation

1. **Enable financial aggregates in production** — backfill + `FINANCIAL_AGGREGATES_ENABLED=true`; validate p95 < 300 ms.
2. **Redis cache layer** — optional `REDIS_URL`; shared L1 for multi-worker ([`06_CACHE.md`](06_CACHE.md)).
3. **Apply TimescaleDB retention** — [`scripts/retention-policies.sql`](../../../scripts/retention-policies.sql) after backup ([`12_DATABASE_RETENTION.md`](12_DATABASE_RETENTION.md)).

---

## P1 — Real-time

1. **SSE pub/sub migration** — Redis publish from `SnapshotWriter`; remove 1 s DB poll loops ([`07_REALTIME.md`](07_REALTIME.md)).
2. **Pi SSE** — replace 4 s poll in `usePiDashboardData` with authenticated EventSource; keep LKG fallback.

---

## P2 — Smart energy (product)

From [`docs/emic-analysis/21_UNUSED_OPPORTUNITIES.md`](../21_UNUSED_OPPORTUNITIES.md) and Phase 1 foundations:

| Feature | Foundation | Package |
|---------|------------|---------|
| **Battery Opportunity Engine** | `UnifiedEnergyState`, price engine, energy control | `energy_optimizer/eov.py` (stub) |
| **Horizon Optimizer** | Forecast snapshots, flexible load horizon | `energy_optimizer/`, `flexible_load/horizon.py` |
| **Energy control activation** | Slow lane `energy_control` sync | `energy_control/service.py` |

Wire optimizers through `UnifiedEnergyState` adapters rather than parallel dict payloads.

---

## P2 — Observability

1. Collector lane dashboard in frontend (consume `tasks.lanes` from performance API).
2. Integration health UI panel (extend diagnostics page).
3. Alerting on `consecutive_failures > N` for heartbeat provider.

---

## P3 — Testing & CI

1. Fix pre-existing `ChargerSetupWizard.test.tsx` failure.
2. Add `phase1-baseline.ps1` to CI smoke (against staging).
3. Load test financial-stats with aggregates enabled (10 users).

---

## Suggested Phase 2 sequence

```
Auth hardening → Financial flag rollout → Re-benchmark
    → Redis (if multi-worker) → SSE pub/sub → Pi SSE
    → Battery Opportunity Engine → Horizon Optimizer
    → Retention policies
```

Detailed architecture notes: [`docs/emic-analysis/23_ARCHITECTURE_RECOMMENDATIONS.md`](../23_ARCHITECTURE_RECOMMENDATIONS.md).
