# Phase 19 — CI Baseline Smoke

## Goal

Automate post-deploy smoke checks and document CI parity.

## Deliverables

- `scripts/phase19-baseline-smoke.ps1` — quick 200-check on key routes
- Extended `scripts/phase1-baseline.ps1` route list (battery, horizon, current price)
- GitHub Actions `benchmark-smoke` job (`workflow_dispatch`)

## Usage

```powershell
.\scripts\phase19-baseline-smoke.ps1 -BaseUrl http://192.168.50.54
```
