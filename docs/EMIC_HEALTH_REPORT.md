# EMIC Health Report — Audit & Stabilisering

**Datum:** 2026-08-29  
**Teststatus:** 757 pytest + 433 Vitest + 7 .NET — alla gröna  
**Migration head:** `044_encrypted_integration_credentials`

---

## Sammanfattning

Fas 0–7 genomförd enligt plan. Akuta produktionsbuggar (konfidens, intervall, valuta) åtgärdade. Datakedjan skyddar befintliga mätvärden vid degraderade Heartbeat-svar. Frontend och backend konsoliderade. Död kod borttagen. Prestanda förbättrad via rollups och index. Säkerhetshårdning utan ny autentisering (LAN-antagande).

---

## Fas 0 — Konfidensregression ✅

| Problem | Åtgärd |
|---------|--------|
| `confidence` 0–100 skrevs till API som 0–1 | `_normalize_confidence()` i `intelligence_bridge.py` |
| UI visade 5800 % | Frontend får nu ~0.58 |
| `quality: HIGH` trots `Low` label | `_map_quality()` jämför korrekt skala |

---

## Fas 1 — Enheter, intervall, tidszoner ✅

- **`intervals.py`:** `infer_interval_hours_from_timestamps`, `power_to_energy_kwh`
- **Engine/physical_model:** dynamiskt intervall istället för fast `INTERVAL_HOURS=0.25`
- **Frontend:** `inferForecastIntervalMs` i `chartTime.ts`, UTC-etiketter fixade
- **Tidszoner:** platslokalt datum i solar intelligence service/repo

---

## Fas 2 — Valuta ✅

- Migration **041:** `spot_price_sek_kwh` → `spot_price_eur_kwh`, `all_in_price_sek_kwh` → `all_in_price_eur_kwh`
- **`market_prices/currency.py`:** central `eur_to_sek`, `effective_price_sek_kwh`
- **`EUR_TO_SEK_RATE`** i config (default 11.0)
- Alla kostnadsvägar (EV, consumer, spa, financial stats) konverterar EUR→SEK

---

## Fas 3 — Datakedjans integritet ✅

- **`present_fields`** på `RawEnergyReading` — spårar vilka fält som kom från provider
- Collector skippar degraderade readings utan mätningar
- **Villkorlig upsert** — uppdaterar bara fält som faktiskt rapporterades
- **EV accounting** skippar nollutfyllnad vid saknad live-overview
- **Heartbeat client:** tomma payloads cachas inte; 5xx-retry; `resilient_call` på fler endpoints

---

## Fas 4 — Konsolidering ✅

- **`lib/chartTime.ts`:** tid, intervall, energi-summor
- **`createSectionNavigation`:** generisk sektionsnavigering (5 dashboards)
- **`energy/integration.py`:** delad dags-kWh-trapetsintegration (300 s cap)
- Diurnal-kurva: kanonisk `diurnal_solar_factor` i `constants.py`

---

## Fas 5 — Död kod ✅

Borttaget 12 ersatta komponenter + 11 tester + `useSiteCache.ts`.  
Backend: `_diurnal()`, `widget_savings_cache_seconds`.  
Charger-katalog markerar ej implementerade märken tydligt.

---

## Fas 6 — Prestanda ✅

- **`rollup_queries.py`:** solar queries via `energy_hourly`/`energy_daily`
- Migration **042:** index på `ev_charging_sessions.status`, `flexible_load_plan`, `heartbeat_discovery_runs`
- N+1 fix: `get_latest_for_sites`, widget batch snapshots
- Frontend: deduplicerade dashboard-hämtningar, stabil memo i `ProductionForecastPanel`, delad live-overview i collector

---

## Fas 7 — Databas & säkerhet ✅

- Migration **043:** UNIQUE `(site_id, heartbeat_ev_id)` med dedupe
- Migration **044:** krypterade credentials (Fernet/SecretBox-mönster)
- **`CHARGEAMPS_MOCK`:** fail-hard i produktion
- **Postgres:** inget default-lösenord i compose
- **Deploy-script:** lösenord inte längre på kommandorad
- **Healthchecks** på backend, frontend, collector

---

## EMIC Health Score (0–100)

| Område | Betyg | Kommentar |
|--------|-------|-----------|
| Korrekthet (enheter, TZ, valuta) | **88** | EUR-kolumner rename klart; växelkurs fortfarande config-default |
| Dataintegritet | **85** | Zerofill skyddat; SEMP processlokal state kvarstår (dokumenterad) |
| Testtäckning | **92** | +37 pytest, +10 vitest sedan baseline |
| Frontend UX/konsistens | **86** | chartTime + section factory; vissa lokala formatters kvar |
| Backend/prestanda | **84** | Rollups + index; vissa endpoints kan mätas vid deploy |
| Integrationer/resiliens | **83** | Heartbeat retry/LKG; Mercedes WS-manager ej inkopplad |
| Säkerhet (LAN) | **78** | Credential-kryptering; ingen ny auth (medvetet) |
| Driftbarhet | **80** | Healthchecks, deploy-script; kräver `EMIC_SECRET_KEY` + `POSTGRES_PASSWORD` |

### **Sammanvägt EMIC Health Score: 85 / 100**

*(Baseline före audit: ~62 — regressioner i prod, zerofill, fel valuta, duplicerad logik)*

---

## Kvarstående risker

1. **`EUR_TO_SEK_RATE`** bör kopplas till live-kurs eller manuell admin-uppdatering
2. **`virtual_evse/store.py`** processlokal — SEMP tom state mellan containrar
3. **Mercedes `ConnectionManager`** finns men används inte i `provider.py`
4. **Migration 041–044** måste köras på prod (`alembic upgrade head`)
5. **`EMIC_SECRET_KEY`** krävs för credential-kryptering efter migration 044

---

## Deploy-checklista

```powershell
# Sätt i .env på servern:
# POSTGRES_PASSWORD=...
# EMIC_SECRET_KEY=...
# CHARGEAMPS_MOCK=false
# EUR_TO_SEK_RATE=11.0  # eller aktuell kurs

.\test-windows.ps1          # lokalt — grönt
.\scripts\deploy-linux.ps1  # deploy + migration
```

Verifiera efter deploy:
- Solar forecast `confidence` ≈ 0.58 (inte 58.0)
- `quality` följer `confidence_label`
- Inga noll-skrivningar i readings vid simulerat Heartbeat-fel
- Alla dashboard-vyer utan console errors
