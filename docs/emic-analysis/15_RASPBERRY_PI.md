# EMIC Raspberry Pi Kiosk

**Primary doc:** `docs/PI_KIOSK.md`  
**Scripts:** `scripts/pi/kiosk/`  
**Frontend:** `frontend/src/app/display/`  
**Backend:** `backend/app/display_service.py`, `backend/app/display_auth.py`

---

## 1. Architecture

```
Chromium (Wayland/labwc)
  → http://127.0.0.1:8080/display/{slug}
  → Pi Caddy (emic-caddy.service)
      → injects Authorization: Bearer on /api/* only
  → https://emic.inacloud.se (EMIC server)
      → Caddy → frontend:3000 + backend:8000
```

| Component | Detail |
|-----------|--------|
| Hardware | Raspberry Pi 3 Model B Plus (EMIC-MON) |
| OS | Debian 13 (trixie), aarch64 |
| Display | 7" HDMI 1024×600, no EDID |
| Compositor | labwc via lightdm (Wayland, not X11) |
| Browser | Chromium 151, native Wayland, kiosk mode |
| RAM | 905 MiB total (~490 MiB used with kiosk) |
| systemd | `emic-kiosk.service`, `emic-caddy.service`, `emic-display-color.service` |

---

## 2. Authentication

| Property | Value |
|----------|-------|
| Token storage | `/etc/emic/kiosk.env` (chmod 600, never committed) |
| Scope | `display.read` device token |
| Injection | Pi Caddy adds Bearer header for `/api/*` only |
| Chromium | Never sees token |
| Direct API | Returns 401 without proxy |
| Enrollment | `GET /api/v1/display/enroll` (hidden from schema) |

**Security:** Good pattern — token not in browser storage.

---

## 3. API & Polling

| Property | Value |
|----------|-------|
| Endpoint | `GET /api/v1/display/overview/{slug}` |
| Frontend hook | `usePiDashboardData.ts` |
| Poll interval | **4 seconds** (exponential backoff to 30s on error) |
| Server cache | 3s overview, 60s weather (`display_service.py`) |
| Connection banner | `PiConnectionBanner.tsx` — shows offline state |

---

## 4. Touch Navigation

| Route | Section |
|-------|---------|
| `/display/{slug}` | Home — all live cards |
| `/display/{slug}/solar` | Sol |
| `/display/{slug}/energy` | Energi |
| `/display/{slug}/battery` | Batteri |
| `/display/{slug}/grid` | Nät |
| `/display/{slug}/vehicle` | Fordon |
| `/display/{slug}/charger` | Laddbox |
| `/display/{slug}/spa` | Spa |
| `/display/{slug}/economy` | Ekonomi |
| `/display/{slug}/insights` | Höjdpunkter |

Sections defined: `frontend/src/components/pi-dashboard/piSections.ts`  
Home button: 56px top-left on all views.

---

## 5. Failure Scenarios

### 5.1 Internet Lost (Pi → EMIC server)

| Behavior | Current | Recommended |
|----------|---------|-------------|
| API calls fail | Backoff to 30s polling | ✅ |
| UI display | Connection banner; stale data may remain visible | Show last-known-good timestamp |
| Cached data | Client keeps last successful response in React state | ✅ partial |
| Offline mode | **Not implemented** | Cache last overview in localStorage/IndexedDB |

### 5.2 EMIC Server Down

Same as internet loss from Pi perspective. Caddy on Pi may still serve cached static assets for frontend shell but API fails.

### 5.3 Heartbeat Down

| Layer | Behavior |
|-------|----------|
| Collector | Readings stop updating; snapshots age |
| Display API | Serves stale snapshot from DB (last successful collector write) |
| Pi UI | Shows aged data without explicit "Heartbeat offline" message |
| Freshness section | `DisplayFreshnessSection` in overview — shows data age if populated |

### 5.4 API Down (backend unavailable)

Pi Caddy cannot reach remote → 502/connection error → client backoff + connection banner.

### 5.5 Partial Degradation (Mercedes/Spa down)

Display overview builds sections independently — vehicle/spa sections show unavailable/stale while core energy may still update.

---

## 6. Last-Known-Good Requirements

**User requirement:** Dashboard should show last-known-good data when services fail.

| Data | LKG support |
|------|-------------|
| Core energy (readings) | ✅ via DB snapshot (until retention expires) |
| Display overview | ⚠️ Server cache 3s only — no persistent LKG |
| Pi client | ⚠️ React state holds last response until unmount |
| Weather | 60s server cache |
| Vehicle | LKG merge in vehicle repo (collector-side) |
| Explicit "data from X min ago" | Partial via freshness section |

**Gap:** Pi should persist last successful overview locally and display prominently when offline.

---

## 7. Network Configuration

- eth0 + wlan0 on same subnet; eth0 preferred (metric 100 vs 600)
- Split-horizon DNS to LAN IP supported
- WiFi system connection for boot without login

---

## 8. Display Tuning

Scripts: `tune-display-color.sh`, `set-display-mode.sh`, `detect-drm-crtc.sh`  
Pinned mode: 1024×600 @ 59.951 Hz (`hdmi_force_hotplug=1` — no EDID)  
Color service: `emic-display-color.service`

---

## 9. Phase 2 Gaps (documented, not in API)

Per `docs/PI_KIOSK.md`, detail views show `--` for:
- Solar forecast curve
- Battery charge/discharge today
- Price min/max
- Charger decision reason
- Spa filter-cycle counts
- Vehicle target SoC

**Backend data may exist** in other endpoints but not aggregated into `display_service.py`.

---

## 10. Chromium / Kiosk Hardening

| Control | File |
|---------|------|
| Kiosk flags | `chromium-kiosk.sh` |
| Policy | `chromium-policy.json` |
| Disable blanking | `disable-blanking.sh` |
| Disable desktop dialogs | `disable-desktop-dialogs.sh` |
| No new tabs | Kiosk mode + in-app links only |

---

## 11. Recommendations

1. **Persist LKG** on Pi (localStorage + timestamp banner)
2. **SSE instead of 4s poll** — reduce load, instant updates
3. **Extend display_service** with Phase 2 fields from existing data
4. **Offline shell** — show cached overview with gray overlay when API unreachable >30s
5. **Health indicator** on home: Heartbeat age, snapshot age, connection status
6. **Reduce poll to 8–10s** aligned with server cache

---

## 12. UNKNOWN

- Pi behavior after 24h continuous offline
- Chromium memory leak rate on Pi 3 over weeks
- Whether SSE works through Pi Caddy proxy to remote EMIC
