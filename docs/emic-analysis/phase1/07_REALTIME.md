# Real-Time — Design Only (SSE Pub/Sub)

**Status:** DESIGN ONLY — no migration in Phase 1  
**Reference:** [`docs/emic-analysis/08_REALTIME_DATA.md`](../08_REALTIME_DATA.md)

---

## Current architecture

| Client | Mechanism | Interval |
|--------|-----------|----------|
| Pi kiosk | HTTP poll | 4 s ([`usePiDashboardData.ts`](../../../frontend/src/lib/usePiDashboardData.ts)) |
| Dashboards | HTTP poll | 15–60 s |
| SSE streams | DB poll loop | 1 s check in [`snapshot.py`](../../../backend/app/api/snapshot.py) `/live-stream`, `/kiosk/stream` |

Each SSE connection independently polls PostgreSQL for `generated_at` changes — N clients = N poll loops.

Pi kiosk does **not** use SSE today (poll only).

---

## Problem

- SSE endpoints scale poorly: 1 s × connections × sites.
- Pi 4s polling generates steady load but is simpler to reason about.
- No cross-worker event bus — snapshot updates invisible to other uvicorn workers without DB round-trip.

---

## Proposed migration (Phase 2)

### Phase A — Redis pub/sub (optional dependency)

```
Collector SnapshotWriter
    → UPSERT site_live_snapshots
    → PUBLISH emic:events:{site_slug} {"type":"snapshot","generated_at":"..."}

Backend SSE handler
    → SUBSCRIBE emic:events:{site_slug}
    → Push to client on message (no 1s DB poll)
```

### Phase B — Pi SSE adoption

Replace 4 s poll in `usePiDashboardData` with `EventSource` to `/api/v1/display/stream/{slug}` (new route or extend kiosk stream with display auth).

Fallback: keep LKG localStorage ([`08_PI.md`](08_PI.md)) on disconnect.

### Phase C — Unified channel

Single event envelope:

```json
{"site_slug":"akarp","type":"snapshot|prices|vehicle","payload_ref":"db|inline","ts":"..."}
```

Frontend hooks subscribe once per site; route events to React context providers.

---

## Success criteria (when implemented)

| Metric | Target |
|--------|--------|
| Live state propagation | < 2 s (baseline ~10 s snapshot age — already LIVE) |
| SSE DB queries per client | 0 (event-driven) |
| Pi display latency | < 100 ms perceived update |

---

## Why deferred in Phase 1

- Requires Redis or equivalent pub/sub (see [`06_CACHE.md`](06_CACHE.md)).
- Pi LKG + poll backoff delivers offline resilience without SSE complexity.
- Dashboard routes already meet p95 target without SSE.
