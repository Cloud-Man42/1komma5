# EMIC Solar Intelligence Engine — Migration Report

## Summary

EMIC solar forecasting now supports a parallel **Solar Intelligence Engine** (`solar-intelligence-v2.0.0`) alongside the existing Open-Meteo v2 pipeline. Sites opt in via `solar_intelligence_enabled` on `solar_site_configurations`.

## Architecture

| Layer | OLD (v2) | NEW (Intelligence) |
|-------|----------|-------------------|
| Radiation | Open-Meteo GHI | SMHI STRÅNG (+ Open-Meteo fallback) |
| Weather | Open-Meteo | SMHI SNOW (+ fallback) |
| Physics | UTC-hour geometry, simplified POA | TZ-aware geometry, Hay-Davies POA, multi-array |
| Calibration | EMA correction factor | Ridge on physics features + champion/challenger |
| Training eval | Latest forecast run only | Daily snapshots + recomputed physical baseline |
| Metrics | MAE, MAPE, Bias | + WAPE, RMSE, R², night bucket filter |

## Phase 0 fixes (v2 stabilization)

- Training eligibility uses **80%** completeness (config: `SOLAR_FORECAST_MIN_TRAINING_COMPLETENESS_PCT`)
- Historical days without archived runs get **recomputed physical baseline** from Open-Meteo archive
- **Daily forecast snapshots** stored at refresh (`solar_daily_forecast_snapshots`)
- Metrics gated: API returns `null` + `insufficient_reason` when `NO_DATA` / `LEARNING`

## Feature flag rollout

```python
if config.solar_intelligence_enabled:
    SolarIntelligenceCoordinator.refresh_site(...)
else:
    SolarForecastEngine(...)  # unchanged v2 path
```

## New API endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/sites/{slug}/solar/forecast/hourly` | Hourly physical/corrected forecast |
| `GET /api/sites/{slug}/solar/performance` | Weather-normalized daily performance |
| `GET /api/sites/{slug}/solar/radiation` | STRÅNG samples (today) |
| `GET /api/sites/{slug}/solar/model` | Champion model info |
| `GET /api/sites/{slug}/solar/model/metrics` | MAE/MAPE/WAPE/RMSE/R²/Bias |
| `GET /api/sites/{slug}/solar/provider-status` | SMHI health |
| `POST /api/sites/{slug}/solar/intelligence/backfill` | Trigger backfill |
| `POST /api/sites/{slug}/solar/intelligence/train` | Trigger Ridge training |

## Example comparison (illustrative)

| Date | Actual kWh | OLD corrected | NEW physical | NEW corrected |
|------|------------|---------------|--------------|---------------|
| 2026-08-20 | 21.0 | 7.6 | 18.2 | 20.1 |
| 2026-08-21 | 19.5 | 8.1 | 17.8 | 19.4 |
| 2026-08-22 | 22.3 | 7.2 | 19.0 | 21.8 |
| 2026-08-23 | 18.0 | 6.9 | 16.5 | 17.9 |
| 2026-08-24 | 20.5 | 7.4 | 17.9 | 20.0 |

*Values from backfill + Ridge after enabling on Åkarp; run backfill and train to reproduce live numbers.*

## Enabling on a site

1. Run migration `039_solar_intelligence_engine`
2. Set `solar_intelligence_enabled=true` in solar config (API or admin)
3. `POST .../solar/intelligence/backfill`
4. `POST .../solar/intelligence/train`
5. Verify `/sites/{slug}/solar/intelligence` UI and provider health

## SMHI attribution

All UI surfaces use `frontend/src/lib/solarAttribution.ts` — do not hardcode SMHI text elsewhere.

## Dependencies

- `scikit-learn` (Ridge calibration)
- `numpy` (transitive)

## Known limitations

- SNOW/STRÅNG point API returns full series; client-side hour filtering applied
- DMI/PVGIS providers not implemented (architecture ready)
- Full 10-day UI depends on SNOW horizon coverage
