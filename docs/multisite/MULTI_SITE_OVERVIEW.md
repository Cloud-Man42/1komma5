# EMIC Multi-Site Overview

## Architecture

EMIC supports **single-site** dashboards at `/sites/{slug}` and a **multi-site overview** at `/overview` when the user selects two or more accessible sites.

- Site identity: numeric `id` in DB, **`slug` in URLs/API**
- User access: `emic_user_site_access` (binary); RBAC permissions are global
- Selection persistence: `emic_user_site_preferences.selected_site_slugs` (JSON array)
- Aggregation: `MultiSiteAggregationService` reuses `EnergyStateService.build_snapshots_batch()`

## Site selection

| Selection count | Behaviour |
|-----------------|-----------|
| 0 (edge) | Empty state — prompt to select sites |
| 1 | Redirect to `/sites/{slug}` (existing dashboard) |
| 2+ | `/overview` multi-site dashboard |

Preferences are sanitized on every read/write against the user's current `site_ids`. Revoked access removes slugs automatically.

## RBAC

- `GET /api/sites` and overview endpoints require authentication + `dashboard.read`
- `POST /api/multi-site/overview` verifies **every** requested slug is in `principal.site_ids`
- Unauthorized slugs → HTTP 403 (no data leakage)

## Aggregation rules

### Sum (additive)

- Momentane effekt (W/kW): solar, consumption, grid import, grid export, battery charge/discharge, EV
- Dagens energi (kWh): production, consumption, import, export, battery charged/discharged
- Kostnad/besparing **within the same currency only**

### Weighted (not arithmetic mean of percentages)

- **Combined battery SoC** = `sum(stored_kwh) / sum(usable_capacity_kwh)`
- **Self-consumption %** = aggregated self-consumed solar / aggregated solar production
- **Self-sufficiency %** = aggregated self-consumed / aggregated consumption

### Do not sum

- Raw SoC % across sites
- Spot prices across price areas (show per site or per area)
- Temperature, individual health labels

### Grid

Always expose separately:

- `grid_import_kw` (sum)
- `grid_export_kw` (sum)
- `grid_net_kw` = export − import (signed)

### Timezone

"Today" is computed **per site** in that site's `timezone`, then daily totals are summed for the overview.

### Currency

Resolved from `site.energy_economics_country`: SE→SEK, DK→DKK. Costs are grouped by currency; **never** sum SEK + DKK without FX (not in v1).

### Partial data

If any selected site fails or lacks readings, aggregated KPIs sum only available sites and set `dataQuality.partial = true` with `sitesAvailable / sitesRequested`.

## Cache

Key: `emic:multisite:{sorted_slugs_csv}:overview`  
TTL: 45s (aligned with dashboard refresh). Slugs sorted for stable keys.

## API

```
POST /api/multi-site/overview
{ "site_slugs": ["akarp", "summer-house-denmark"] }

GET  /api/user/site-selection
PATCH /api/user/site-selection
{ "selected_site_slugs": ["akarp"] }
```

## Frontend

- `SiteSelectionProvider` — global selection state + persistence
- `SiteSelector` — multi-select in `DashboardTopBar` and home page
- `/overview` — two-column dashboard:
  - **Live power flow** — radial hub diagram with one house node per site (color-coded)
  - **Generation, grid and battery – 24h** — KPI strip + chart (aggregate areas + per-site solar lines)
  - **Anläggningar i vyn** — visibility chips (click toggle, double-click isolate)
  - Site cards, cost breakdown (filtered by visible sites)

### Site visibility (view filter)

Separate from site **selection** (which sites are included in the overview API call):

| Action | Effect |
|--------|--------|
| Click chip | Show/hide site in flow, chart, KPIs, cost, header |
| Double-click chip | Isolate one site |
| Visa alla | Restore all selected sites |

Hidden sites remain in the card list (dimmed) for quick re-enable. Header shows `N av M anläggningar i vyn` when filtered.

Client-side re-aggregation: `aggregateSiteEntries`, `aggregateSiteCurrencies`, `aggregateSiteHealth` in `frontend/src/lib/multiSiteClientAggregate.ts`.

## Acceptance checklist

| Item | Status |
|------|--------|
| Site selector | PASS |
| Multi-select | PASS |
| Persisted selection | PASS |
| Single-site preserved | PASS |
| Multi-site overview | PASS |
| Weighted battery SoC | PASS |
| Grid import/export separate | PASS |
| Currency handling | PASS |
| RBAC | PASS |
| Partial data | PASS |
| Unit tests | PASS |
