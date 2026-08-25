# EMIC Apple Widget

Native iPhone client and WidgetKit extension for read-only energy status from EMIC.

## Architecture

```text
Heartbeat / Sungrow / Charge Amps / Modbus
              │
              ▼
         EMIC Collector
              │
              ▼
      energy_readings (+ related DB state)
              │
              ▼
     EnergyStateService (DB-only)
              │
              ▼
   GET /api/v1/widget/*  (Bearer device token)
              │
              ▼
   EMIC iOS app + EMICWidgets extension
```

The Widget API never contacts external integrations directly. It reads persisted EMIC state only.

## Power sign convention

| Field | Sign | Meaning |
|-------|------|---------|
| `solar.powerKw` | `> 0` | PV production |
| `house.powerKw` | `> 0` | House consumption |
| `battery.powerKw` | `> 0` | Battery charging |
| `battery.powerKw` | `< 0` | Battery discharging |
| `grid.powerKw` | `> 0` | Grid import |
| `grid.powerKw` | `< 0` | Grid export |
| `ev.powerKw` | `> 0` | EV charging |

Missing values are returned as JSON `null`. Clients must render `—` / `Ej tillgänglig`, never `0.0` as a substitute.

## Authentication

1. Open EMIC admin: `/config` → **Apple-enheter**
2. Create a device for each user (e.g. Henriks iPhone, Annas iPhone)
3. Copy the one-time token (`emic_…`) and paste it into the EMIC iOS app onboarding screen
4. Token is stored in Keychain (`group.net.inacloud.emic`) — never in UserDefaults or source code
5. Revoke lost devices from `/config`

Device tokens require scope `widget.read` only.

## Widget API

Base path: `/api/v1/widget`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/sites` | Site list with `systemStatus` |
| GET | `/status` | Default site for device |
| GET | `/status/{siteId}` | Specific site (`akarp`, `summer-house-denmark`) |
| GET | `/summary` | All sites + totals |
| GET | `/me` | Token validation / profile |

Admin (existing EMIC UI, no device token):

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/apple-devices` | List devices |
| POST | `/api/apple-devices` | Create device (returns token once) |
| POST | `/api/apple-devices/{id}/revoke` | Revoke |
| PATCH | `/api/apple-devices/{id}` | Rename |
| GET | `/api/apple-devices/metrics` | In-process widget metrics |

OpenAPI tag: **Apple Widget API** (`/docs`).

## Configuration

Environment variables (see `.env.development.example`):

- `WIDGET_STALE_SECONDS` (default 120)
- `WIDGET_SNAPSHOT_CACHE_SECONDS` (default 15)
- `WIDGET_SAVINGS_CACHE_SECONDS` (default 300)
- `WIDGET_RATE_LIMIT_PER_MINUTE` (default 60)

## Local development (no Docker)

```powershell
make backend-dev
make collector-dev
```

Register a device via `POST /api/apple-devices` or `/config`, then call:

```http
GET http://localhost:8000/api/v1/widget/status/akarp
Authorization: Bearer emic_...
```

## iOS project (macOS / Xcode)

The Xcode project is generated with [XcodeGen](https://github.com/yonaskolb/XcodeGen):

```bash
cd apple
brew install xcodegen   # once
xcodegen generate
open EMIC.xcodeproj
```

### Required Xcode steps

1. Set **Development Team** for targets `EMIC`, `EMICWidgets`, `EMICKit`
2. Enable **App Groups**: `group.net.inacloud.emic` on app + widget
3. Enable **Keychain Sharing**: `$(AppIdentifierPrefix)net.inacloud.emic.shared`
4. Add widget extension to the EMIC scheme
5. Run on a physical device (WidgetKit + Keychain sharing are limited on Simulator)
6. Configure server URL + device token in the app

Bundle IDs (defaults):

- App: `net.inacloud.emic.app`
- Widget: `net.inacloud.emic.widgets`
- Framework: `net.inacloud.emic.kit`

## Production deployment

Widget API is included in the existing backend container. Ensure Caddy exposes `/api/*` over **HTTPS** before exposing Widget API to the Internet.

Recommended Caddy addition (not enabled in repo by default):

```caddy
header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
```

Do not expose the Widget API over plain HTTP in production.

## App Group shared data

- Last successful widget snapshot (`SnapshotStore`)
- Preferred site slug
- Server base URL (non-secret)

Credentials remain in Keychain only.

## Contract tests

Backend writes golden JSON to `apple/Fixtures/`. Swift tests in `EMICKitTests` decode the same files to prevent schema drift.

## Troubleshooting

| Symptom | Check |
|---------|-------|
| 401 Unauthorized | Token revoked or wrong Bearer header |
| 403 Forbidden | Device missing `widget.read` scope |
| 429 Too Many Requests | Rate limit; WidgetKit will retry later |
| Stale widget | Collector not running or `WIDGET_STALE_SECONDS` exceeded |
| Keychain errors on Simulator | Use a device; verify App Group + Keychain entitlements |

## Future extensions

The same DTOs and auth model are intended for Apple Watch, Lock Screen widgets, Live Activities, and push (APNs) without backend redesign.
