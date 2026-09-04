# EMIC Raspberry Pi 7" Kiosk

Dedicated wall display for Åkarp at `/display/akarp`, served through a local Caddy proxy on the Pi.

## Architecture

- **Pi:** `EMIC-MON`, Raspberry Pi 3 Model B Plus — DHCP on both `eth0` and
  `wlan0`, so it answers on two addresses. Replaced the original board, which is
  what fixed the colour fault below.
- **Pi URL (browser):** `http://127.0.0.1:8080/display/akarp`
- **EMIC server:** `https://emic.inacloud.se` (split-horizon DNS to the LAN IP is fine)
- **API:** `GET /api/v1/display/overview/akarp` (requires `display.read` device token)
- **Token storage:** `/etc/emic/kiosk.env` (`chmod 600`, never committed)

Caddy on the Pi injects `Authorization: Bearer …` for `/api/*` requests only. Chromium never sees the token, and the route is not public — requesting the API directly without the proxy returns `401`.

```
Chromium → 127.0.0.1:8080 (emic-caddy) → https://emic.inacloud.se (EMIC)
                ↑ Bearer token on /api/*
```

## Touch navigation (Pi-only)

The kiosk is a **touch-first panel**, not a desktop web app. The decorative
left sidebar was removed; every card on the home screen is a full-surface touch
target that navigates to a detail view. A **Home** button (56 px, top-left) is
present on every view.

| Route | View |
|-------|------|
| `/display/akarp` | Home — all live cards |
| `/display/akarp/solar` | Sol |
| `/display/akarp/energy` | Energi / förbrukning |
| `/display/akarp/battery` | Batteri |
| `/display/akarp/grid` | Nät & energiflöde |
| `/display/akarp/vehicle` | Fordon |
| `/display/akarp/charger` | Laddbox |
| `/display/akarp/spa` | Spa |
| `/display/akarp/economy` | Ekonomi |
| `/display/akarp/insights` | Dagens höjdpunkter |

Navigation stays inside the kiosk: cards are `<a>` links (no `target="_blank"`),
browser back works, and Chromium kiosk mode never opens new tabs. Cards show a
discreet `›` affordance and scale to `0.98` on press (`touch-action:
manipulation`).

The Pi kiosk URL in `/etc/emic/kiosk.env` is unchanged (`/display/akarp`). No
Pi-side config update is required after a frontend deploy.

Dev preview (mockup data, fixed clock): `/display/preview` and
`/display/preview/{section}`.

**Phase 2 (in API since Phase 21):** solar forecast curve, battery
charge/discharge today, price min/max, charger `decision_reason_sv`, spa
filter-cycle counts (`completed/target`), vehicle `target_soc_pct`. See
`GET /api/v1/display/overview/{slug}`.

## Pi inventory (EMIC-MON, 192.168.0.112)

| Item | Value |
|------|-------|
| Hostname | EMIC-MON |
| OS | Debian 13 (trixie), aarch64, kernel 6.18.39+rpt |
| Session | **Wayland / labwc** via lightdm (not X11) |
| Chromium | 151.0.7922.173, run as a native Wayland client |
| Panel | 7" HDMI, **no EDID** (`edid` is 0 bytes, `hdmi_force_hotplug=1`) |
| Active mode | **1024×600 @ 59.951 Hz** (pinned, see below) |
| RAM | 905 MiB total (~490 MiB used with kiosk running) |
| systemd units | `emic-caddy.service`, `emic-display-color.service`, `emic-kiosk.service` |
| Network | eth0 `192.168.0.112`, wlan0 `192.168.0.111` on `Zmilla-ATV` |

### Network

Both interfaces sit on `192.168.0.0/24` behind the same gateway. NetworkManager
manages them; the wifi profile is a **system connection** (`connection.permissions`
empty) so it comes up at boot without a login.

Ethernet keeps priority through its route metric — 100 for eth0 against 600 for
wlan0 — so the cable is used whenever it is plugged in and wifi is the fallback.

```bash
sudo nmcli connection add type wifi con-name '<SSID>' ifname wlan0 ssid '<SSID>' \
  wifi-sec.key-mgmt wpa-psk wifi-sec.psk '<password>' connection.autoconnect yes
sudo nmcli connection up '<SSID>'
```

A wrong password shows up as `4-Way Handshake failed` / `reason=WRONG_KEY` in
`journalctl -u NetworkManager`, which `nmcli` reports only as the misleading
"Secrets were required, but not provided".

### Why the display mode must be pinned

The panel supplies no EDID, so wlroots falls back to a generic mode list whose
first entry is `1024x768` and treats that as "preferred". The kernel cmdline
already carries `video=HDMI-A-1:1024x600@60D`, but that only sets the initial
framebuffer — the compositor still picked 1024×768, which letterboxed the
dashboard.

The fix is a kanshi profile (`~/.config/kanshi/config`). kanshi is started by
`/etc/xdg/labwc/autostart` on every session, so the mode is applied at login.
`set-display-mode.sh` runs as `ExecStartPre` for the kiosk unit as a safety net
and waits up to 30 s for the compositor, so a cold boot cannot race the session.

### Display colour — resolved by replacing the Pi

The dashboard needs no colour correction. It once did, and the record below
matters only if the symptom ever returns.

#### The symptom

Measured with `scripts/pi/kiosk/colortest.html`, the panel mixed its colour
channels: **pure red showed magenta, green showed cyan, blue showed yellow**,
while the full grey ramp stayed neutral. That is a linear channel mix

```
displayed = P · sent        P = [1 0 1]
                                [0 1 1]
                                [1 1 0]
```

and because `P` maps grey to grey, gamma, colour temperature and the panel's own
R/G/B sliders could not touch it — they scale channels, they cannot unmix them.
The mix appeared above roughly 40 MHz pixel clock: clean at 800×600 (40.0 MHz)
and 640×480 (25.2 MHz), mixed at the panel's native 1024×600 (48.9 MHz).

#### The cause

Blamed on the hand-wired HDMI leads and on mechanical stress on the panel board
— loosening the screws that clamped it visibly reduced the mix, which was
misleading. **Replacing the Raspberry Pi removed the mix entirely**, with the
same panel, the same leads and the same 1024×600 mode. The suspicion is
contamination from thermal paste near the SoC on the first board, bridging or
loading the HDMI output.

The lesson: a symmetric channel mix that survives every software knob is a
hardware fault on the *sending* side. Swap the board before writing a matrix.

#### What was removed

The dashboard used to pre-multiply by `P⁻¹` in an `feColorMatrix` in
`display/layout.tsx`, with a `?panelfix=off` switch to re-check the panel. All of
it is gone: the filter, the `--pi-color-filter` CSS variable, `lib/panelColorFix.ts`
and the `?panelfix=off` parameter on the tablet enrolment redirect.

If a channel mix ever appears again, do not restore the filter. Confirm which
side is at fault first by moving the panel to another machine.

Note that `set-display-mode.sh` runs as `ExecStartPre`, so a manual `wlr-randr`
mode change is undone on the next kiosk restart. Change `EMIC_KIOSK_MODE` and
`kanshi-config` to make a different mode stick.

#### Brightness

The panel exposes **no backlight class and no DDC/CI** (`ddcutil detect` finds no
display, since there is no EDID), so the Pi cannot change the backlight. Real
brightness is only available from the **panel's own OSD**; keep it at
**R=G=B=100 (Mode USER)**.

The surface design tokens (`--pi-page`, `--pi-card`, …) are pinned to the mockup
values. Lifting them to brighten the screen was tried and read purple, but that
attempt overlapped with the colour fault above and was never re-tested on the
new Pi.

Device-side colour still runs through `start-display-color.sh`, which applies
`EMIC_KIOSK_COLOR_TEMP` (4000 K) and a per-channel `EMIC_KIOSK_GAMMA_RGB`
(`1.35_1.08_0.70`) via DRM gamma. Those values were tuned against the old board;
set `EMIC_KIOSK_GAMMA_RGB=1_1_1` in `/etc/emic/display.env` and restart
`emic-display-color` to judge the new one neutral.

Keep the panel OSD at **R=100, G=100, B=100 (Mode USER)** — the compensation
assumes a neutral OSD.

#### Optional DRM gamma (disabled)

`emic-display-color.service` exists for genuine white-balance needs and runs
gammastep via **DRM** (labwc does not implement `wlr-gamma-control`, so Wayland
gamma is a silent no-op — it reports `Zero outputs support gamma adjustment`).
It is **installed but not enabled**, because stacking it with the channel fix
double-corrects. Enable only if the panel is replaced and needs warming:

```bash
sudo systemctl enable --now emic-display-color.service
~/emic-kiosk/tune-display-color.sh 4000 1.20_1.0_0.85   # live preview
```

| Variable | Default | Purpose |
|----------|---------|---------|
| `EMIC_KIOSK_COLOR_TEMP` | `4000` | Colour temperature in Kelvin (lower = warmer) |
| `EMIC_KIOSK_GAMMA_RGB` | `1.35_1.08_0.70` | Red:green:blue multipliers (`_` in env, `R:G:B` in config) |

Chromium runs with `--force-color-profile=srgb`.

## Register Pi device

In EMIC config (`/config`) or via API:

```http
POST /api/apple-devices
{
  "owner_label": "Henrik",
  "device_name": "Pi 7\" Display",
  "device_type": "raspberry_pi",
  "default_site_slug": "akarp"
}
```

Save the returned token once — it is only shown at creation. Scope is automatically set to `display.read`, which `device_type` `raspberry_pi` and `tablet` both receive.

## Other screens: tablet, phone, laptop

The Pi is the only device with a local proxy injecting the bearer token, so any
other browser has to carry its own credential. Register a device and open the
enrollment link once on that screen:

```http
POST /api/apple-devices
{ "owner_label": "Henrik", "device_name": "Surfplatta", "device_type": "tablet", "default_site_slug": "akarp" }
```

```
http://<emic-host>/api/v1/display/enroll?token=<token>
```

The endpoint validates the token, stores it in an `HttpOnly`, `SameSite=Lax`
cookie valid for a year, and redirects to `/display/<slug>`. After the redirect
the token is gone from the address bar and history, and it is never readable from
JavaScript. Add `&slug=<other-site>` to override the device's default site.

Notes:

- The cookie only carries the `display.read` scope, so an enrolled screen can
  read the dashboard and nothing else. `POST /api/apple-devices/<id>/revoke`
  locks it out immediately.
- The cookie is marked `Secure` only when the request arrives over HTTPS, since
  the LAN deployment (`Caddyfile`) serves plain HTTP and would otherwise drop it.
- The layout adapts on its own: the frame scales by
  `min(width / 1024, height / 600)`, so any tablet aspect ratio works.

## A second site (Denmark)

Nothing in the dashboard is Sweden-specific — every route, API call and section is
keyed on the site slug, so `/display/summer-house-denmark` works exactly like
`/display/akarp`. What differs per site is provisioning:

| Screen | What to do |
|--------|-----------|
| Pi | Run the installer with the site and server as parameters (below) |
| Tablet | Open the enrollment link with `&slug=summer-house-denmark` |

A site-to-site VPN already links Åkarp and Denmark firewall to firewall, so a
Danish Pi reaches the EMIC server on its LAN address exactly like the Swedish
one. Only the site differs:

```bash
EMIC_SITE_SLUG=summer-house-denmark sudo -E bash /tmp/emic-kiosk/setup-kiosk.sh
```

`sudo -E` matters: without it sudo drops the variable and you get the Swedish
default. Reaching EMIC across some other path is a parameter too — set
`EMIC_SERVER` and `EMIC_SERVER_SCHEME=https` for a public endpoint. All of it
lands in `/etc/emic/display.env`, which both the Caddyfile placeholders and the
kiosk scripts read, so no file in the repo needs editing per site. Re-running the
installer without these variables leaves an existing Pi untouched, so a
hand-tuned URL survives an upgrade.

### Connecting the Danish house to live data

The collector skips any site without an `external_system_id` — see
`SitePollContext.live_overview` and `_collect_market_prices` — so readings and
prices stay empty until the house is mapped to its Heartbeat system. Attach it
whenever the installation exists, from `/config` or directly:

```http
PUT /api/sites/summer-house-denmark
{ "external_system_id": "<heartbeat-system-id>" }
```

Until then the dashboard still renders, and says so: the header banner reports
`Inaktuella värden — N dagar sedan senaste mätning` whenever the newest reading
is older than the staleness threshold. A reachable API is not the same as live
data, and the kiosk must never present a two-week-old number as current.

Money is modelled in SEK throughout (`fallback_purchase_price_sek_kwh` and
friends), so a Danish site reports its economy in SEK, not DKK.

## Install on Pi

```bash
scp -r scripts/pi/kiosk hm@192.168.0.112:/tmp/emic-kiosk
ssh hm@192.168.0.112
bash /tmp/emic-kiosk/normalize.sh   # only needed when copied from a Windows checkout
sudo bash /tmp/emic-kiosk/setup-kiosk.sh
```

### Configuration files

Two files, split so the bearer token never enters Chromium's environment:

| File | Mode | Loaded by | Contents |
|------|------|-----------|----------|
| `/etc/emic/kiosk.env` | `600` root | `emic-caddy.service` | `EMIC_KIOSK_TOKEN` only |
| `/etc/emic/display.env` | `644` root | `emic-kiosk.service`, `emic-caddy.service`, `emic-display-color.service` | `EMIC_SITE_SLUG`, `EMIC_SERVER`, `EMIC_SERVER_SCHEME`, `EMIC_KIOSK_URL`, `EMIC_KIOSK_HEALTH`, `EMIC_KIOSK_MODE`, colour vars |

`emic-caddy.service` loads both: the token from `kiosk.env` and the upstream
address from `display.env`. Chromium only ever sees `display.env`, so the token
still never reaches the browser's environment.

> The display settings originally lived in `kiosk.env`, which
> `emic-kiosk.service` never loaded — so every `EMIC_KIOSK_URL` or
> `EMIC_KIOSK_MODE` edit was silently ignored and the scripts fell back to their
> built-in defaults. `emic-display-color.service` could not read it either, since
> it runs as `hm` and the file is root-only. Run `migrate-display-env.sh` once on
> an existing Pi, or re-run `setup-kiosk.sh`, which migrates automatically.

The setup script:

1. Inventories OS, compositor, Chromium, and display modes
2. Prompts for the device token (hidden input) unless `/etc/emic/kiosk.env` exists
3. Installs the kanshi mode profile and the Chromium enterprise policy
4. Installs systemd units `emic-caddy`, `emic-display-color`, and `emic-kiosk`
5. Disables the apt `caddy.service` (conflicts on admin port 2019)
6. Masks sleep targets, writes the logind drop-in, adds `consoleblank=0`

## Files

| File | Purpose |
|------|---------|
| `setup-kiosk.sh` | Idempotent installer for everything below |
| `Caddyfile` | Local proxy; injects the bearer token on `/api/*`, upstream from `EMIC_SERVER` |
| `kiosk-target.sh` | Resolves the site slug and EMIC server; sourced by the kiosk and diagnostic scripts |
| `emic-caddy.service` | Proxy unit, loads `/etc/emic/kiosk.env` (the token) |
| `emic-display-color.service` | gammastep colour temperature for the HDMI panel |
| `emic-kiosk.service` | Chromium unit, `Restart=always`, loads `/etc/emic/display.env` |
| `migrate-display-env.sh` | One-off split of `kiosk.env` into `display.env` for existing Pis |
| `start-display-color.sh` | Optional DRM gamma via gammastep (service disabled by default) |
| `tune-display-color.sh` | Live preview helper for colour tuning |
| `detect-drm-crtc.sh` | Resolves the active CRTC index for gammastep |
| `set-broadcast-rgb.sh` | Forces Broadcast RGB=Full on the HDMI connector |
| `colortest.html` | Colour test pattern for characterising the panel |
| `chromium-kiosk.sh` | Chromium launch flags + health watchdog |
| `chromium-policy.json` | Enterprise policy (suppresses translate bubble etc.) |
| `kanshi-config` | Pins HDMI-A-1 to 1024×600 |
| `set-display-mode.sh` | Mode safety net, waits for the compositor |
| `disable-blanking.sh` | Wayland-correct blanking prevention |
| `disable-desktop-dialogs.sh` | Masks keyring prompt, on-screen keyboard, polkit agents |
| `wayland-env.sh` | Resolves `WAYLAND_DISPLAY` for systemd-launched helpers |
| `screenshot.sh` | `grim` capture for verification |
| `verify-boot.sh` | Post-reboot verification report |
| `check-console.sh` | Captures page console errors headlessly |
| `diagnose*.sh` | Read-only inventory of session, Wayland, EDID |
| `normalize.sh` | Strips CRLF after copying from a Windows checkout |

## Chromium kiosk configuration

```
--kiosk
--ozone-platform=wayland --enable-features=UseOzonePlatform
--lang=sv
--force-device-scale-factor=1
--force-color-profile=srgb
--noerrdialogs --disable-infobars
--disable-session-crashed-bubble --disable-restore-session-state
--hide-crash-restore-bubble --hide-scrollbars
--disable-features=Translate,TranslateUI
--disable-pinch --overscroll-history-navigation=0
--disable-component-update --check-for-update-interval=31536000
--password-store=basic
--user-data-dir=/home/hm/.config/emic-kiosk-chromium
```

Native Wayland (`--ozone-platform=wayland`) matters: under Xwayland the page
viewport did not match the panel mode exactly.

`chromium-kiosk.sh` also rewrites `exit_type`/`exited_cleanly` in the profile
`Preferences` before launch, so an unclean shutdown cannot surface a
"restore pages?" bubble over the dashboard.

### Translate bubble

`--disable-features=Translate` is **not** honoured by Chromium 151: the page is
`lang="sv"` while the browser UI is English, so the translate bubble appeared
over the header. It is suppressed by enterprise policy instead:

```
/etc/chromium/policies/managed/emic-kiosk.json → { "TranslateEnabled": false, … }
```

## Nothing may draw over the kiosk

During verification a gnome-keyring **"Unlock Keyring / Authentication
required"** dialog appeared on top of the dashboard, together with
**squeekboard**, the on-screen keyboard (the panel is a touchscreen). A wall
display has nobody to answer a prompt, so every component that can raise a
window is masked per-user via `~/.config/autostart` entries with `Hidden=true`:

```
squeekboard, gnome-keyring-{pkcs11,secrets,ssh}, pprompt,
lxpolkit, polkit-mate-authentication-agent-1
```

`disable-desktop-dialogs.sh` installs those masks and kills anything already
running; `chromium-kiosk.sh` re-kills them at launch as a safety net. The system
`polkitd` daemon still runs — it draws nothing on its own, only the masked
agents did.

To restore any component, delete its file from `~/.config/autostart`.

## Sleep / blanking configuration

`xset s off` / `xset -dpms` do **not** apply on this Pi — the session is
Wayland, so those commands are rejected or affect only Xwayland clients. On
wlroots compositors blanking is driven by an idle daemon, so the measures are:

| Layer | Setting |
|-------|---------|
| Idle daemon | `disable-blanking.sh` kills `swayidle`/`xscreensaver`/`light-locker`; none run by default |
| Output power | `wlopm --on '*'` before Chromium starts |
| logind | `/etc/systemd/logind.conf.d/99-emic-kiosk.conf` → `IdleAction=ignore`, lid/suspend keys ignored |
| System sleep | `sleep.target`, `suspend.target`, `hibernate.target`, `hybrid-sleep.target` masked |
| Console | `consoleblank=0` on the kernel cmdline plus `setterm --blank 0 --powersave off` |

`systemd-inhibit` is deliberately **not** used: as a system unit without a
logind session it fails with "Interactive authentication required" from polkit,
which took the kiosk down. The masked targets plus `IdleAction=ignore` cover the
same ground.

## Logs

```bash
journalctl -u emic-kiosk -u emic-caddy --since today
tail -f ~/.local/share/emic-kiosk/chromium.log
```

## Verification checklist

Run `bash /home/hm/emic-kiosk/verify-boot.sh` after any reboot.

| # | Test | Result |
|---|------|--------|
| 1 | Cold boot → Chromium fullscreen | **Pass** — boot 35.5 s, `graphical.target` at 19 s, 0 unit restarts |
| 2 | Display mode after reboot | **Pass** — kanshi applies 1024×600 automatically |
| 3 | No scrollbars at 1024×600 | **Pass** — fixed grid, `overflow:hidden`, `--hide-scrollbars` |
| 4 | No browser UI / translate bubble | **Pass** — policy suppresses it |
| 4b | No desktop dialogs / on-screen keyboard | **Pass** after masking; keyring prompt + squeekboard were observed before |
| 5 | Live data via proxy | **Pass** — API returns ~19 KB JSON |
| 6 | Unavailable sections show `--` / `Data saknas` | **Pass** — battery SOH, vehicle SoC, spa cleaning |
| 7 | Route not public | **Pass** — direct API call without the proxy returns `401` |
| 8 | EMIC restart → reconnect | **Pass** — stopping EMIC showed a red `OFFLINE` badge, an "Ingen kontakt med EMIC" banner and the last-known timestamp; restarting it recovered to `ONLINE` with no intervention |
| 8b | Page console errors | **Pass** — none; captured headlessly against the proxied URL |
| 9 | `killall chromium` → systemd restart | **Pass** — `Restart=always`, new processes within ~7 s |
| 10 | Sleep/blanking disabled | **Pass** — targets masked, `IdleAction=ignore`, `consoleblank=0`, `IdleHint=no`, no idle daemon |

## Resource usage (post-reboot, idle)

- **Memory:** ~490 MiB used, ~417 MiB available of 905 MiB
- **CPU:** ~3.4 % user / 1.7 % system, 93 % idle
- **Chromium processes:** 10 (main + renderers + GPU)

## Known gaps

- **Battery SOH** shows `--` until Heartbeat exposes state-of-health.
- **Vehicle SoC / range** show `--`: the Mercedes integration currently reports
  no `state_of_charge_percent`. The panel keeps its exact layout regardless.
- **Vehicle heading** reads `FORDON – MERCEDES-BENZ` because EMIC stores both
  make and model as "Mercedes-Benz" for this vehicle. The heading appends the
  model as soon as the DB carries a distinct one.
- **Economy deltas** show `--` until a full previous month of financial data
  exists to compare against.
- **Chromium log noise:** recurring `DEPRECATED_ENDPOINT` (Google GCM
  registration) and `eglCreateContext ES 3.0 … EGL_BAD_ATTRIBUTE` (driver falls
  back to a supported ES version). Neither affects rendering.

## Troubleshooting

### A dialog or keyboard is covering the dashboard

```bash
bash /home/hm/emic-kiosk/disable-desktop-dialogs.sh
sudo systemctl restart emic-kiosk
```

If it came back after a reboot, check that the masks in `~/.config/autostart`
still exist and are owned by `hm`.

### Dashboard is letterboxed / wrong size

The compositor reverted to 1024×768. Check and re-pin:

```bash
wlr-randr | grep current
wlr-randr --output HDMI-A-1 --mode 1024x600
cat ~/.config/kanshi/config    # must contain the panel profile
pgrep kanshi                   # started by /etc/xdg/labwc/autostart
```

### emic-kiosk fails: "Interactive authentication required"

The unit is wrapping Chromium in `systemd-inhibit`. Remove it — see the
sleep/blanking section.

### emic-caddy fails: port 2019 in use

```bash
sudo systemctl disable --now caddy
sudo systemctl restart emic-caddy
```

Ensure `/etc/emic/Caddyfile` contains `admin off` in the global block.

### Proxy returns 200 with empty body

Add `header_up Host emic.inacloud.se` to all `reverse_proxy` blocks in the Caddyfile
(or set `EMIC_SERVER_HOST` in `/etc/emic/display.env`). Without it the upstream
may see `Host: 127.0.0.1:8080` or the raw LAN IP and Caddy on EMIC won't match
the HTTPS site block.

### API returns 401 through proxy

Check the token in `/etc/emic/kiosk.env` and that `emic-caddy.service` loads it
via `EnvironmentFile`.

### Kiosk not starting after reboot

```bash
systemctl status emic-kiosk emic-caddy
journalctl -u emic-kiosk -n 50
```

The kiosk needs the labwc session to exist. `set-display-mode.sh` waits for the
Wayland socket, and the unit restarts every 5 s, so it normally self-heals.

### Scripts fail with "unexpected end of file" or bad option names

The files were copied from a Windows checkout with CRLF line endings. Run
`bash normalize.sh` in the copied directory.
