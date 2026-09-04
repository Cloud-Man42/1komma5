# EMIC Real-Time Data

---

## 1. Mechanisms in Use

| Mechanism | Location | Used by |
|-----------|----------|---------|
| **HTTP polling** | Frontend hooks | All dashboards |
| **SSE (Server-Sent Events)** | `backend/app/api/snapshot.py` | `/live-stream`, `/kiosk/stream` |
| **Collector polling** | `collector/app/collector.py` | Data ingestion |
| **Mercedes WebSocket** | `vehicles/mercedes/transport/websocket_client.py` | Collector supervisor only |
| **In-memory cache TTL** | Various | Snapshot, display, widget |
| **SignalR** | Not used | — |
| **FastAPI WebSocket** | Not used | — |

---

## 2. Update Frequencies

### Server-side (collector)

| Data | Frequency | Source |
|------|-----------|--------|
| Energy readings | 30–60s | Heartbeat |
| Live overview | 1× per collector cycle per site | Heartbeat |
| Site snapshots | Each collector cycle | SnapshotWriter |
| Price periods | Each collector cycle (refresh) | Heartbeat |
| Smart charging decisions | Each collector cycle | SmartChargingEngine |
| Solar forecast | 30 min (due sites) | SolarForecastCoordinator |
| Vehicle state | Adaptive 30s–300s | Mercedes supervisor |
| Arctic Spa | 60s / 15s cleaning | Spa polling |

### Client-side (frontend)

| View | Interval | Endpoint |
|------|----------|----------|
| Pi kiosk | **4s** (backoff 30s) | `/api/v1/display/overview/{slug}` |
| Overview dashboard | 15s + 30s (duplicate) | `/dashboard` |
| Site layout provider | 30s | `/dashboard` |
| Overview extra panels | 60s | solar, history, forecast |
| Energy dashboard | 60s | dashboard, readings |
| EV, Solar, SPA, Vehicle | 30s (config) | Multiple |
| Economy | **None** (mount only) | financial-stats |
| Performance center | 10s | `/system/performance` |
| Sidebar prices | 300s | price-engine |
| Solar layout prefetch | 300s | config, weather |

### SSE

| Stream | Poll interval | Emit condition |
|--------|---------------|----------------|
| `/api/sites/{slug}/live-stream` | 1s DB check | When `generated_at` changes |
| `/api/kiosk/{slug}/stream` | 1s DB check | Same |

---

## 3. Current Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Browser 1  │     │  Browser 2  │     │  Pi Kiosk   │
│  poll 30s   │     │  poll 30s   │     │  poll 4s    │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │ HTTP GET (each client independently)
                           ▼
                    ┌──────────────┐
                    │   Backend    │
                    │  (158 APIs)  │
                    └──────┬───────┘
                           │ DB reads (often uncached)
                           ▼
                    ┌──────────────┐
                    │  PostgreSQL  │
                    └──────▲───────┘
                           │ writes
                    ┌──────┴───────┐
                    │  Collector   │◄──── Heartbeat (30-60s)
                    │  (1 process) │
                    └──────────────┘
```

**Problem:** N clients × M endpoints = multiplicative load, even though collector centralizes ingestion.

---

## 4. Recommended Architecture

```
Device/API (Heartbeat, Charge Amps, Mercedes, Spa, Weather)
         │
         ▼
    COLLECTOR (single ingestion loop)
         │
         ▼
    NORMALIZED ENERGY STATE
    (unified EnergyState + site_live_snapshots)
         │
         ├──► Time-Series DB (readings, aggregates)
         │
         ├──► Cache Layer (Redis: snapshot + LKG + pub/sub)
         │
         ▼
    SSE / WebSocket (push on generated_at change)
         │
         ▼
    CLIENT (single subscription, no per-endpoint polling)
```

### Benefits
- 1 push per client instead of 5–10 polls
- Snapshot age guaranteed consistent across UI
- Backend GET load drops proportionally to client count
- Pi kiosk can hold last event indefinitely (offline LKG)

---

## 5. SSE Current Implementation

**File:** `backend/app/api/snapshot.py`

```python
# Conceptual flow (from code):
async def event_generator():
    while True:
        snapshot = await repo.get_latest(site_id)
        if snapshot.generated_at != last_emitted:
            yield f"data: {json}\n\n"
        await asyncio.sleep(1)  # 1 second DB poll
```

**Issues:**
- DB query every second per SSE connection
- No cross-process notification when collector writes snapshot
- Main dashboards don't use SSE — they HTTP poll instead

---

## 6. Real-Time vs Near-Real-Time Classification

| Data class | Actual latency | Acceptable latency | Status |
|------------|----------------|-------------------|--------|
| Live power | 30–60s | 5–15s | Acceptable for monitoring |
| Battery SOC | 30–60s | 15s | Acceptable |
| EV charging power | 30–60s + control cycle | 10s | Acceptable |
| Vehicle SOC (Mercedes) | 30s–5min adaptive | 60s | OK when charging |
| Prices | 30–60s refresh | 15 min aligned | Over-refreshed |
| Weather | 45 min | 30 min | OK |
| Solar forecast | 30 min | 60 min | OK |
| Economy | Static until reload | 5 min | **Under-served** |

---

## 7. Assessment

**EMIC over-polls on the client** (especially Pi at 4s, overview duplicate at 15s+30s) while **under-using push mechanisms** (SSE exists but unused by main dashboards).

**EMIC correctly centralizes ingestion** in collector (post Performance v2) — the gap is the **last mile to clients**.

### Priority actions
1. Wire main dashboards to SSE or WebSocket snapshot stream
2. Remove duplicate dashboard polls (single coordinator)
3. Redis pub/sub from collector on snapshot write → SSE push (eliminate 1s DB poll)
4. Pi: subscribe to SSE with client-side LKG display on disconnect

---

## 8. Mercedes WebSocket (internal real-time)

- Runs only in collector `VehicleIntegrationSupervisor`
- Not exposed to frontend clients
- Frontend polls REST vehicle endpoints at 30s instead
- **Gap:** Could push vehicle state changes via same SSE channel

---

## 9. UNKNOWN

- Whether any deployment uses SSE live-stream in production browsers
- WebSocket feasibility through Caddy proxy (likely OK but untested in docs)
