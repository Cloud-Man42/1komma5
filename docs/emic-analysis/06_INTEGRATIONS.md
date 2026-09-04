# EMIC External Integrations

All integrations verified from Python codebase. **Not found:** Sensibo, Stripe, direct Nord Pool API, live Modbus, eBEcon.

---

## Integration Summary Table

| Integration | Purpose | Protocol | Auth | Timeout | Rate limit |
|-------------|---------|----------|------|---------|------------|
| 1Komma5 Heartbeat | Energy readings, prices, EV aggregate, Sungrow proxy | HTTPS REST + JWT | Email/password → Bearer JWT | 20s default | UNKNOWN |
| Sungrow | Inverter telemetry | Via Heartbeat live overview | Inherited | 60s stale threshold | N/A |
| Charge Amps | EV charger control/metering | HTTPS REST v5 | API key + email/password | 20s; min poll 15s | Client-side intervals |
| Mercedes | Vehicle telemetry/commands | WebSocket + REST | OAuth login flow | WS ping 30s/32s | Adaptive poll |
| Arctic Spa | Spa status/control | HTTPS REST | X-API-KEY | 10s | Poll 60s/15s |
| ChargeFinder | Away charging lookup | HTTPS web scrape | AES key from web app | 15s | Circuit cooldown 900s |
| Nobil | Station DB (legacy) | DB tables only | N/A | N/A | N/A |
| SMHI | Solar radiation (STRÅNG) | HTTPS open data | None | 30s | UNKNOWN |
| DMI | Weather HARMONIE | HTTPS open data | None | 30s | UNKNOWN |
| Open-Meteo | Weather forecast/archive | HTTPS | Optional API key | 30s | UNKNOWN |
| Mock Heartbeat | Dev/test | In-process | None | N/A | N/A |

---

## 1. 1Komma5 Heartbeat

| Attribute | Detail |
|-----------|--------|
| **PURPOSE** | Primary energy data source: site readings, live overview, market/import/export prices, EV charger aggregate, device commands |
| **PROTOCOL** | HTTPS REST; `onekommafive` Python package |
| **AUTH** | JWT Bearer; login via email/password; token refresh on 401; JWT exp skew 300s |
| **FILES** | `heartbeat_client.py`, `providers/onekommafive.py`, `heartbeat_auth.py`, `heartbeat/*` |
| **CREDENTIALS** | Env `HEARTBEAT_API_URL`, DB `heartbeat_settings` (encrypted via Fernet SecretBox) |
| **ENDPOINTS** | Readings, live overview, market prices, export prices, EV control — via onekommafive SDK |
| **TIMEOUT** | 20s default on `HeartbeatClient` |
| **RETRY** | 401 → token refresh retry; 5xx retry on readings; `resilient_call` wrapper |
| **CACHE** | `LastKnownGoodStore` + `CircuitBreaker` (threshold 3, cooldown 60s) |
| **ERROR HANDLING** | Degraded readings skipped (`reading_is_actionable`); conditional upsert preserves existing fields |
| **FALLBACK** | LKG cache; mock provider in dev (`MockHeartbeatProvider`) |
| **HEALTH CHECK** | `GET /api/system/charging-readiness`; heartbeat audit endpoints |
| **UI IMPACT IF DOWN** | All live data stale; dashboards show last snapshot age; smart charging pauses |

---

## 2. Sungrow (via Heartbeat)

| Attribute | Detail |
|-----------|--------|
| **PURPOSE** | Inverter PV, load, grid, battery telemetry for energy balance |
| **PROTOCOL** | Mapped from Heartbeat live overview JSON |
| **AUTH** | Via Heartbeat |
| **FILES** | `sungrow/heartbeat_provider.py`, `heartbeat/live_overview.py`, `energy_balance/engine.py` |
| **TIMEOUT** | Stale if older than `SUNGROW_TELEMETRY_MAX_AGE_SECONDS` (default 60s) |
| **FALLBACK** | Energy balance marks alignment flags; residual warnings |
| **NOTE** | Direct Modbus removed (migration 012); catalog lists Modbus as future/unimplemented |

---

## 3. Charge Amps

| Attribute | Detail |
|-----------|--------|
| **PURPOSE** | EV charger metering, current control, smart charging |
| **PROTOCOL** | HTTPS REST API v5 + web adapter |
| **AUTH** | `CHARGEAMPS_API_KEY`, `CHARGEAMPS_EMAIL`, `CHARGEAMPS_PASSWORD`; mock via `CHARGEAMPS_MOCK` |
| **FILES** | `chargers/charge_amps.py`, `client.py`, `framework/adapters/charge_amps.py` |
| **TIMEOUT** | 20s; max 3 retries |
| **RATE LIMIT** | Min poll 15s, min write 5s (client-side) |
| **CACHE** | Charger state in DB `ev_chargers.last_*` |
| **ERROR HANDLING** | `assert_chargeamps_production_safe()` at startup |
| **FALLBACK** | Mock adapter in dev |
| **UI IMPACT** | EV dashboard stale; smart charging engine skips control |

---

## 4. Mercedes (Vehicles)

| Attribute | Detail |
|-----------|--------|
| **PURPOSE** | Vehicle SOC, location, charging state, commands (start/stop, target SOC) |
| **PROTOCOL** | WebSocket (protobuf) + REST token refresh |
| **AUTH** | OAuth login; tokens encrypted in `vehicle_provider_connections` |
| **FILES** | `vehicles/mercedes/*`, `vehicles/supervisor.py`, `vehicles/polling.py` |
| **TIMEOUT** | WS ping_interval 30s, ping_timeout 32s; REST refresh 300s |
| **RETRY** | Exponential backoff; circuit breaker after 5 auth failures; failure backoff 900s |
| **CACHE** | `vehicle_state_latest`; LKG merge in repo |
| **FALLBACK** | Mock vehicle provider; stale guard hides old charging LKG |
| **UI IMPACT** | Vehicle dashboard shows stale/unavailable; commands fail gracefully |

---

## 5. Nord Pool / Market Prices

| Attribute | Detail |
|-----------|--------|
| **PURPOSE** | Electricity spot/import/export prices for economics and smart charging |
| **PROTOCOL** | **Not direct Nord Pool** — prices via Heartbeat API |
| **AUTH** | Via Heartbeat JWT |
| **FILES** | `price_engine/providers/heartbeat_market.py`, `heartbeat_export.py`, `price_engine/engine.py` |
| **STORAGE** | `price_periods` (15-min canonical), legacy `market_prices` (hourly) |
| **RETENTION** | 90 days on price_periods |
| **FALLBACK** | `sites.fallback_purchase_price_sek_kwh`, `export_compensation_sek_kwh` |
| **UI IMPACT** | Economy/pricing stale; smart charging uses last known schedule |

---

## 6. SMHI

| Attribute | Detail |
|-----------|--------|
| **PURPOSE** | STRÅNG radiation data, snow data for solar intelligence |
| **PROTOCOL** | HTTPS open-data API |
| **AUTH** | None (public URLs) |
| **FILES** | `solar_intelligence/providers/smhi_strang.py`, `smhi_snow.py` |
| **TIMEOUT** | 30s (`SMHI_TIMEOUT_SECONDS`) |
| **CACHE** | `solar_radiation_samples`, provider health table |
| **FALLBACK** | Open-Meteo / DMI routing in forecast pipeline |

---

## 7. DMI

| Attribute | Detail |
|-----------|--------|
| **PURPOSE** | HARMONIE weather forecast for solar |
| **PROTOCOL** | HTTPS EDR API |
| **AUTH** | None (public) |
| **FILES** | `solar_intelligence/providers/dmi_harmonie.py` |
| **TIMEOUT** | 30s |
| **ENDPOINT** | `GET /api/sites/{slug}/solar/dmi/forecast` |

---

## 8. Open-Meteo

| Attribute | Detail |
|-----------|--------|
| **PURPOSE** | Weather forecast and historical archive for solar forecast |
| **PROTOCOL** | HTTPS |
| **AUTH** | Optional `OPEN_METEO_API_KEY` |
| **FILES** | `solar_intelligence/providers/open_meteo_adapter.py`, `solar_forecast/open_meteo.py` |
| **TIMEOUT** | 30s |
| **CACHE** | 45 min weather cache; `solar_weather_cache` table |

---

## 9. Arctic Spa

| Attribute | Detail |
|-----------|--------|
| **PURPOSE** | Spa status, energy, filter/cleaning control |
| **PROTOCOL** | HTTPS REST |
| **AUTH** | X-API-KEY header; per-site config |
| **FILES** | `integrations/arctic_spa/client.py`, `polling.py`, `control.py` |
| **TIMEOUT** | 10s; 3 retries on 429/503 with exponential backoff |
| **POLL** | 60s default; 15s during active cleaning |
| **ENABLED** | `ARCTIC_SPA_ENABLED` default **false** |
| **FALLBACK** | Spa dashboard shows unavailable; shadow mode available |

---

## 10. ChargeFinder

| Attribute | Detail |
|-----------|--------|
| **PURPOSE** | Find public charging stations when away from home |
| **PROTOCOL** | HTTPS web scraping (no official API) |
| **AUTH** | AES key extracted from ChargeFinder web app JS |
| **FILES** | `integrations/charging_stations/chargefinder/*` |
| **TIMEOUT** | 15s |
| **CIRCUIT BREAKER** | `ChargeFinderCircuitBreaker`; cooldown 900s; captcha/block detection |
| **CACHE** | Geohash DB cache, TTL 604800s (7 days) |
| **UI IMPACT** | Admin/diagnostics only — not on critical dashboard path |

---

## 11. Integrations Causing UI Slowness / Instability

| Integration | Risk | Mechanism |
|-------------|------|-----------|
| Heartbeat | **CRITICAL** | All data depends on it; 20s timeout blocks collector |
| Open-Meteo/SMHI/DMI | **HIGH** | 30s timeouts in solar collector cycle |
| Charge Amps | **MEDIUM** | Write failures affect smart charging; not page-load path |
| Mercedes | **MEDIUM** | Auth failures trigger 900s backoff; vehicle page stale |
| ChargeFinder | **LOW** | Admin only; circuit breaker prevents storms |
| Arctic Spa | **LOW** | Optional; isolated to spa features |

---

## 12. Cascading Failure Paths

```
Heartbeat down
  → No new readings
  → Stale snapshots
  → Smart charging uses stale EnergyState
  → Price engine no refresh
  → Financial stats use fallback prices
  → Dashboards show stale age (should not crash)
```

```
Mercedes auth failure
  → Supervisor backoff 900s
  → Vehicle dashboard stale
  → EV smart charging may lack vehicle SOC (continues with charger data)
```

```
Weather provider down
  → Solar forecast uses LKG/degraded mode
  → Solar intelligence engine returns `_degraded_from_last_good`
```

---

## 13. Credential Exposure Audit

| Credential | Stored | Frontend exposure |
|------------|--------|-------------------|
| Heartbeat JWT/password | DB encrypted + env | Config UI shows connection status, NOT raw secrets |
| Charge Amps | Env + per-charger DB | `/api/system/chargeamps-config` returns status only |
| Mercedes tokens | DB encrypted | Integration config endpoints mask secrets |
| Arctic Spa API key | DB/env | Spa config test endpoints server-side only |
| Display/Widget tokens | DB hash + Pi env file | Pi Caddy injects Bearer; Chromium never sees token |
| Fernet key | `emic-secret.key` / Docker volume | Never exposed via API |

**Verify:** API schemas use response models excluding password fields — spot-check `HeartbeatConfigResponse`, `ChargeAmpsConfigResponse` in `backend/app/schemas.py`.

---

## 14. UNKNOWN

- Heartbeat API official rate limits
- SMHI/DMI rate limits
- Production Charge Amps concurrent connection limits
- eBEcon — not in codebase
