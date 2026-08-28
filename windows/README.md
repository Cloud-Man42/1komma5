# EMIC Windows Taskbar Widget

Native Windows 11 client that lives in the **notification area** (taskbar corner, near the clock). Left-click opens a compact energy flyout; the app uses the same read-only Widget API as the iPhone client.

## Requirements

- Windows 10/11
- .NET 8 SDK (build) or .NET 8 Desktop Runtime (run published exe)
- EMIC device token (`emic_…`) registered at `/config` → **Widget-enheter** with platform **Windows**

## Build & run (dev)

From the **repo root** (not `C:\Windows\System32`):

```powershell
cd C:\Users\hm\Projects\1komma5\windows
dotnet run --project EMIC.Tray\EMIC.Tray.csproj
```

Or use the helper script from repo root:

```powershell
.\scripts\run-windows-widget.ps1
```

On first launch, enter:

1. **Server-URL** — e.g. `http://localhost:8000` or your HTTPS domain
2. **Device-token** — from admin UI (shown once)
3. **Standardplats** — `akarp` or `summer-house-denmark`

Credentials are stored under `%APPDATA%\EMIC\` (settings JSON + DPAPI-protected token).

## Usage

- **Green tray icon** — fresh data
- **Yellow** — stale snapshot (`isStale`)
- **Red** — error / not configured
- **Left click** — open/close flyout above taskbar
- **Right click** — context menu (refresh, settings, exit)
- Auto-refresh every 60 seconds

## Publish single-folder exe

```powershell
cd windows
dotnet publish EMIC.Tray -c Release -r win-x64 --self-contained false
```

Output: `EMIC.Tray\bin\Release\net8.0-windows\win-x64\publish\EMIC.exe`

Pin `EMIC.exe` to Start if desired; the widget itself runs from the notification area.

## Tests

Contract tests decode `apple/Fixtures/widget-status-akarp.json` (shared with backend/iOS).

```powershell
cd windows
dotnet test
```

Included in repo-wide `.\test-windows.ps1`.

## Architecture

```text
EMIC.Tray (WPF + NotifyIcon)
    └── EMIC.Core (HTTP client, models, DPAPI storage)
            └── GET /api/v1/widget/*
```

See also `docs/windows-widget.md`.
