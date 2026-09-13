# EMIC Mobile PWA — Architecture Analysis

Date: 2026-09-12

## Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 15 App Router, React 19, TypeScript |
| Styling | CSS modules per dashboard + `mobile-app.css` |
| Charts | recharts 2.x (+ Pi kiosk custom SVG) |
| Backend | FastAPI, energy-core aggregation |
| Auth | Session cookies + CSRF, RBAC, site access |
| Deploy | Docker standalone frontend |

## Routing inventory

### Public (no auth middleware)
- `/login`, `/display/*` (Pi kiosk)

### Dashboard
- `/` — redirects via site selection
- `/overview` — multi-site desktop overview
- `/app` — **mobile PWA home** (new)
- `/app/sites|energy|control|more|install|diagnostics` — mobile hubs (new)
- `/sites/[slug]/*` — full site dashboards (energy, solar, ev, vehicle, spa, costs, diagnostics)

### Admin / config
- `/config/*`, `/admin/*`, `/account`

## Multi-site today

- `SiteSelectionProvider` persists selection via `PATCH /api/user/site-selection`
- 1 site → `/sites/{slug}`; 2+ → `/overview`
- `POST /api/multi-site/overview` aggregates live + today + health + currencies
- Client-side visibility filter on overview page

## Auth / RBAC

- Permissions: `dashboard.read`, `charging.read/control`, `spa.read/control`, `users.read`, etc.
- Site isolation via `emic_user_site_access` enforced server-side
- Frontend `useAuth().can(permission)` for UI gating only

## PWA status (before this work)

| Item | Status |
|------|--------|
| Web manifest | **Missing** |
| Service worker | **Missing** |
| App icons | **Missing** |
| Install prompt | **Missing** |
| Offline shell | **Missing** |
| `theme-color` / Apple meta | **Missing** |

## Desktop-only assumptions

1. **Dashboard sidebar** — rich sub-nav hidden at ≤900px with no mobile replacement
2. **Wide tables** — admin users/roles, config module store, audit logs
3. **Hover interactions** — some config overflow menus
4. **Horizontal scroll top nav** — only mobile nav on site dashboards
5. **Multi-column grids** — overview, economy, energy panels assume ≥768px
6. **Modals** — desktop-centered, not bottom sheets
7. **Config hub sidebar** — collapses awkwardly on phone

## Single-site assumptions

- Most `/sites/[slug]/*` pages assume one active slug from URL
- Multi-site aggregation only on `/overview` and new `/app`
- Currency/price area per site — must not sum across areas incorrectly

## Mobile gaps (priority)

| Gap | Severity | Mitigation |
|-----|----------|------------|
| No installable PWA | Critical | manifest + SW + icons |
| No mobile home summary | Critical | `/app` + mobile summary API |
| No bottom navigation | High | `MobileAppShell` |
| Sidebar lost on mobile | High | Bottom nav + hub pages |
| Small touch targets | Medium | 44px min, bottom sheets |
| Charts clipped on phone | Medium | Responsive recharts, compact axes |
| Admin tables | Medium | Card layout under `/app/more` |
| No offline UX | Medium | Banner, disable controls |
| No safe-area insets | Low | `env(safe-area-inset-*)` padding |

## Kiosk isolation

- `/display/*` uses separate layout, no AppChrome, no mobile shell
- Must remain untouched by PWA navigation injection

## Feature matrix (initial)

| Feature | Desktop | Mobile PWA | Status |
|---------|---------|------------|--------|
| Home summary | `/overview` | `/app` | PASS |
| Site dashboard | `/sites/[slug]` | `/sites/[slug]` + mobile shell | PASS |
| Multi-site select | SiteSelector | Bottom sheet | PASS |
| Solar | `/sites/.../solar` | `/app/energy/solar` | PASS |
| Battery / grid / consumption | `/sites/.../energy` | `/app/energy/*` | PASS |
| Economy | `/sites/.../costs` | `/app/energy/economy` | PASS |
| Forecast | solar/intelligence | `/app/energy/forecast` | PASS |
| History | energy#historik | `/app/energy/history` | PASS |
| Charging / SPA / vehicle | site sub-routes | `/app/control/*` | PASS |
| Health | diagnostics | `/app/more/health` | PASS |
| Account | `/account` | `/app/more/account` | PASS |
| Admin users | table | MobileUserCard | PASS |
| Config / admin | `/config`, `/admin` | `/app/more/admin` | PASS |
| Pi kiosk | `/display/*` | N/A | PASS (unchanged) |
| PWA install | — | `/app/install` | PASS |

## API strategy

- **`POST /api/mobile/summary`** — extends multi-site overview with `warnings`, `quickActions`, mobile-oriented freshness labels
- Reuses `MultiSiteAggregationService` (no duplicate aggregation logic)
- Single request for home screen (no 20 parallel frontend calls)

## Security constraints

- Service worker **must not** cache `/api/*` auth responses, control endpoints, or admin data
- User switch must clear client summary cache
- Offline: read-only summary optional; **never queue control commands**

## Implementation phases

1. **Foundation** — manifest, SW, icons, analysis doc (this file)
2. **App shell** — top bar, bottom nav, offline banner, `/app` layout
3. **Home summary** — hero, flow, today, battery, sites, warnings, quick actions
4. **Hub pages** — sites, energy, control, more
5. **Deep views** — mobile polish on existing routes (incremental)
6. **Admin cards** — mobile user management
7. **Install UX** — QR page, iOS instructions, diagnostics
