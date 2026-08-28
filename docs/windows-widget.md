# EMIC Windows Taskbar Widget

Windows client for read-only EMIC energy status in the **notification area** (Windows 11 taskbar corner).

Microsoft's built-in Widgets panel (Win+W) does not support arbitrary third-party energy widgets today. EMIC therefore ships a **NotifyIcon + flyout** pattern — the standard approach for always-visible taskbar-adjacent status on Windows.

## Same backend as iPhone

Uses `/api/v1/widget` with Bearer `emic_…` tokens. Register devices at `/config` → **Widget-enheter** → platform **Windows (taskbar)**.

## Setup

1. Deploy EMIC backend with Widget API (see `docs/apple-widget.md`).
2. Create a Windows device in admin UI; copy the one-time token.
3. Build or download `EMIC.exe` (see `windows/README.md`).
4. First run: paste server URL + token.
5. **Dra chipet** längs taskbar för att placera det bredvid väder-widgeten (Microsoft tillåter inte tredjepartsappar i samma inbyggda slot).

## Taskbar-chip

- Kompakt text: `Demo Home  Sol 5,4 kW  Bat 74 %`
- **Dra** horisontellt längs taskbar
- **Klick** → detaljerad flyout
- **Högerklick** → meny
- Standard: **Taskbar (som väder)** i Inställningar

## Security

- Token stored with Windows DPAPI (`CurrentUser`) — not plain text on disk.
- Use HTTPS in production before using tokens outside LAN.
- Revoke lost PCs from `/config`.

## Files

| Path | Purpose |
|------|---------|
| `windows/EMIC.Core/` | API client, DTOs, formatters, storage |
| `windows/EMIC.Tray/` | WPF tray host + flyout + settings |
| `windows/EMIC.Core.Tests/` | Fixture + formatter tests |
| `apple/Fixtures/` | Shared JSON contract |
