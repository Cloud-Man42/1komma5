# EMIC Mobile PWA

Date: 2026-09-12

## Overview

EMIC is available as an installable Progressive Web App with a mobile-first home at `/app`. Desktop and kiosk routes remain unchanged.

## Architecture

| Layer | Path |
|-------|------|
| PWA entry | `/app` (`manifest.start_url`) |
| Mobile summary API | `POST /api/mobile/summary` |
| Aggregation | Reuses `MultiSiteAggregationService` |
| Site selection | Shared `SiteSelectionProvider` |
| Kiosk | `/display/*` — no mobile shell |

## Home summary

Sections on `/app`:

1. Status header (selected sites, online count)
2. Hero — total power now
3. Energy flow (vertical)
4. Today — kWh + currencies (never summed across SEK/DKK)
5. Battery storage (weighted SoC)
6. Needs attention (warnings)
7. Quick actions (RBAC filtered)
8. Site cards → `/sites/{slug}`

## Navigation

Bottom tabs:

- **Home** — `/app`
- **Sites** — `/app/sites`
- **Energy** — `/app/energy` → existing site routes
- **Control** — `/app/control` → EV, SPA, vehicle
- **More** — config, admin, install, diagnostics

## PWA install

- Manifest: `/manifest.webmanifest`
- Service worker: `/sw.js` (shell only, no API cache)
- Install guide: `/app/install` with QR to public URL
- Diagnostics: `/app/diagnostics`

## Offline

- Banner when `navigator.onLine === false`
- No control command queue
- Summary shows last error / empty state when offline

## Security

- Service worker does not cache `/api/*`
- Session auth unchanged
- User switch clears via full page navigation on logout

## Responsive

- Phone: single column
- Tablet landscape: two-column home grid (820px+)
- Desktop: `/overview` and `/sites/*` layouts preserved

## Testing

- `packages/energy-core/tests/mobile/test_summary.py`
- `backend/tests/test_mobile_api.py`
- `frontend/src/app/app/page.test.tsx`
- `frontend/src/components/mobile/MobileBottomNav.test.tsx`

## Mobile routes

| Route | Purpose |
|-------|---------|
| `/app` | Home summary |
| `/app/energy/*` | Solar, battery, grid, consumption, forecast, economy, history |
| `/app/control/*` | Charging, SPA, vehicle |
| `/app/more/*` | Health, account, admin hub |
| `/app/sites/[slug]` | Per-site mobile summary |

Global `MobileAppShell` wraps `/sites/*`, `/overview`, `/config`, `/admin`, `/account` on mobile viewport.

## Remaining work

- Web Push notifications (future — architecture documented below)
- Physical device QA matrix (see device test section)

## Web Push (future)

Planned alerts: site offline, battery fault, charging issue, integration failure. Requires backend subscription storage and VAPID keys — not implemented.

---

## Implementation status (2026-09-12)

| Area | Status |
|------|--------|
| Mobile app shell (global on mobile) | **PASS** |
| Home summary | **PASS** |
| Single-site summary | **PASS** |
| Multi-site summary | **PASS** |
| Site selector (bottom sheet) | **PASS** |
| Energy flow | **PASS** |
| Solar / Battery / Grid / Consumption | **PASS** — `/app/energy/*` |
| Economy / Forecast / History | **PASS** |
| Charging / SPA / Vehicle | **PASS** — `/app/control/*` |
| Health | **PASS** — `/app/more/health` |
| User account | **PASS** — `/app/more/account` |
| Admin (mobile cards) | **PASS** — `MobileUserCard` on mobile viewport |
| RBAC / site access | **PASS** |
| Offline banner + no control queue | **PASS** |
| Freshness labels | **PASS** — top bar |
| PWA manifest + PNG icons | **PASS** |
| Service worker (shell only) | **PASS** |
| Install flow + QR + native prompt | **PASS** |
| Diagnostics | **PASS** |
| iOS / Android / Tablet | **PARTIAL** — needs physical device QA |
| Performance (single summary API) | **PASS** |
| Security (no API cache) | **PASS** |
| Kiosk preserved | **PASS** |
| Build | **PASS** |
| Tests | **PASS** |

## Device test matrix (manual QA)

| Device | Browser / mode | Status |
|--------|----------------|--------|
| iPhone | Safari | Pending |
| iPhone | Installed PWA | Pending |
| iPad | Safari / PWA | Pending |
| Android phone | Chrome / PWA | Pending |
| Android tablet | Chrome | Pending |
| Desktop | Edge PWA | Pending |

### Entry points

- Mobile home: `/app`
- Desktop multi-site: `/overview`
- PWA manifest start URL: `/app`
