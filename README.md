# piCalendar

An always-on glass family-calendar display for a Raspberry Pi 3 driving a TV.
Seven-day view of every Google Calendar on your account plus a weekly
forecast from Open-Meteo. Soft atmospheric aesthetic with real
`backdrop-filter` glass, warm ivory in daylight, deep oceanic at night,
switched at your local sunrise and sunset. 100% on-device — no cloud.

| | |
| :-: | :-: |
| Day | Night |
| _warm dawn ivory, terracotta accent_ | _deep oceanic, peach accent_ |

## Requirements

- Raspberry Pi 3 (or newer) running Raspberry Pi OS **Bookworm** with desktop
- A 16:9 display via HDMI — the layout scales fluidly from 1366×768 through 3840×2160
- A Google account with the calendars you want to see
- ~15 minutes

## Architecture

```
Pi 3
 ├─ systemd: picalendar.service ─── python -m backend.app   (Flask on :5000)
 │                                    ├─ /api/events     [5-min TTL cache]
 │                                    ├─ /api/weather    [30-min TTL cache]
 │                                    └─ /                index.html + assets
 └─ LXDE autostart: chromium-browser --kiosk http://localhost:5000
```

Vanilla HTML + CSS + JS on the frontend — no React, no bundler. The Pi 3's
GPU is weak, so the frontend is hand-tuned: one painterly CSS background,
two blur tiers, no live animations behind glass, and a perf probe that
degrades gracefully if the first frames take too long.

## Install on the Pi

```bash
cd ~
git clone <this-repo> picalendar
cd picalendar
bash scripts/install.sh
```

Then:

1. **Set your location.** Edit `~/picalendar/config.json` — latitude,
   longitude, and timezone. A sample is provided in `config.example.json`.
2. **Get Google OAuth credentials.**
   - https://console.cloud.google.com/apis/credentials
   - Create a project (or pick one) → enable the **Google Calendar API**
   - _OAuth consent screen_ → External → fill in required fields → Publish
   - _Credentials_ → _Create credentials_ → _OAuth client ID_ → **Desktop
     app**
   - Download the JSON, save it on the Pi at
     `~/.config/picalendar/credentials.json`
3. **Authorize once.** On the Pi with a keyboard attached:
   ```bash
   cd ~/picalendar
   .venv/bin/python -m backend.oauth_init
   ```
   A browser opens, you sign in, the token is saved to
   `~/.config/picalendar/token.json`.
4. **Start it.**
   ```bash
   sudo systemctl start picalendar
   ```
5. **Reboot** to launch kiosk:
   ```bash
   sudo reboot
   ```

That's it — the calendar comes up on the TV.

## Configuration

`config.json`:

| Key | What |
| --- | --- |
| `latitude` / `longitude` | For weather + sunrise/sunset |
| `timezone` | IANA zone, e.g. `America/New_York` |
| `location_label` | Shown in the header (e.g. `"Washington, DC"`) |
| `fixtures` | `true` to run with demo data (no Google auth needed) |
| `theme_override` | `"day"` or `"night"` to pin; `null` for auto |

## Local development (no Pi, no Google auth)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
PICAL_FIXTURES=1 .venv/bin/python -m backend.app
# open http://127.0.0.1:5000
```

Fixture mode serves a realistic hand-crafted week that exercises
overlap, all-day, and multi-day events.

## Why each piece is the way it is

- **Flask, not FastAPI** — trivial systemd unit, stdlib-only deployment,
  centralizes OAuth refresh so the frontend can poll blindly.
- **Vanilla JS** — no build step, long-lived kiosk tab, the Pi 3 doesn't
  have headroom for a framework runtime.
- **`backdrop-filter` everywhere** — it's the whole aesthetic. The
  Chromium kiosk flags in `scripts/kiosk-autostart` include
  `--ignore-gpu-blocklist`, which is required or VideoCore IV falls back
  to a CPU blur path that tanks the frame rate.
- **Open-Meteo** — no API key, returns sunrise/sunset alongside the
  forecast, so theme-switching and weather are the same request.
- **Daily 3 AM reload** — kills long-lived-page state drift without
  anyone noticing.

## Troubleshooting

**Glass looks chunky / FPS drops on the Pi.** Open DevTools remotely
from another machine on the LAN at `http://<pi-ip>:9222`. Rendering →
enable _Highlight layers_. Glass surfaces should each be their own layer
(GPU-composited). If they are not, confirm the kiosk flags include
`--ignore-gpu-blocklist --use-gl=egl`. As a fallback, the frontend will
flip `data-perf="lite"` automatically if the first frames take >40 ms —
blur radii halve and the ambient drift stops.

**OAuth token expired / calendar empty.** Re-run
`python -m backend.oauth_init` on the Pi. It's idempotent; if your token
is just refreshable, a new call will see the existing token and exit.

**Clock drift / wrong timezone.** Make sure the Pi has `chrony` (default)
and that `config.json`'s `timezone` matches `timedatectl` output.

## File map

```
backend/
  app.py                # Flask routes + cache wiring
  google_calendar.py    # OAuth + multi-calendar fetcher
  weather.py            # Open-Meteo client
  oauth_init.py         # One-shot `python -m backend.oauth_init`
  cache.py              # TTL dict cache
  fixtures.py           # Demo data for local dev

frontend/
  index.html
  styles.css            # Design tokens, glass, fluid scaling, themes
  app.js                # Fetch loop, week render, collision layout, theme
  assets/fonts/         # (optional self-hosted) Fraunces + Geist WOFF2s

scripts/
  install.sh            # apt + pip + systemd + kiosk autostart
  picalendar.service    # systemd unit
  kiosk-autostart       # Chromium kiosk snippet for LXDE autostart

config.example.json
requirements.txt
```
