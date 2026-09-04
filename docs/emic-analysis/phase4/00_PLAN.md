# Phase 4 — Integration Health Expansion & Energy Strategy Diagnostics

**Deployed:** 2026-09-03 to `http://192.168.50.54`

## Delivered

| Item | Change |
|------|--------|
| **Provider health writes** | Collector records `price_engine`, `solar_forecast`, `arctic_spa`, `energy_control` per site |
| **Diagnostics UI** | Swedish provider labels in `IntegrationHealthPanel` |
| **Energy strategy** | `EnergyStrategyCard` on site diagnostics page (EOV / price strategy) |

## Providers tracked

| Provider | Lane | Source |
|----------|------|--------|
| `heartbeat` | fast | live overview prefetch |
| `price_engine` | fast | market price refresh |
| `arctic_spa` | medium | spa polling |
| `solar_forecast` | slow | observation + forecast refresh |
| `energy_control` | slow | strategy sync (non MONITOR_ONLY sites) |
