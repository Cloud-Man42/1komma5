# Phase 25 — Drift, performance, infra verify, product UI

**Date:** 2026-09-04  
**Site:** `akarp`

---

## Delivered

| # | Item | Change |
|---|------|--------|
| 1 | Drift | `phase25-automatic-monitor.ps1`; docs refresh |
| 2 | Performance | Solar snapshot fast path + L1 warm; **server p95 7 ms** (external ~167 ms LAN) |
| 3 | Infra | Timescale policies applied; `GET /api/system/timescale-status` |
| 4 | Product | `Co2TodayCard`, `EnergyBalanceQualityCard` on intelligence overview |

---

## Scripts

```powershell
.\scripts\phase25-automatic-monitor.ps1
.\scripts\phase25-timescale-verify.ps1
.\scripts\phase25-solar-forecast-benchmark.ps1
```
