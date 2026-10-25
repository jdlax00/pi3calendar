# Mom's vertical calendar — setup

Raspberry Pi 3B+ driving a 31.5" TV mounted **portrait, rotated clockwise
(the TV's top edge goes to the right)**. This branch (`mom-vertical`) shows
an agenda: a big Today card plus the next 7 days, each with its weather.

Do it in this order: boot the Pi at your place → dry run with demo data →
connect her calendar → mount and rotate the TV at her house.

---

## 1. Boot the Pi

What you need: Pi 3B+, the official **5.1V 2.5A** micro-USB power supply
(underpowered supplies cause throttling and Chromium crashes), a 16–32 GB
microSD card, HDMI cable, USB keyboard + mouse for setup.

1. **Flash the card** with Raspberry Pi Imager:
   - Device: **Raspberry Pi 3**
   - OS: **Raspberry Pi OS (64-bit)** — the desktop version, not Lite
   - Edit settings:
     - Hostname `momcal`, username `pi`, a password you'll remember
     - Wi-Fi: **her** network name and password (or plan on Ethernet)
     - Locale/timezone: hers (e.g. `America/Denver`)
     - Services: **enable SSH**
2. **First boot** on any screen, landscape is fine. Plug in power and wait
   2–3 minutes. Open a terminal and update:
   ```bash
   sudo apt update && sudo apt full-upgrade -y && sudo reboot
   ```
3. **Install the app from this branch:**
   ```bash
   git clone -b mom-vertical https://github.com/jdlax00/pi3calendar.git ~/picalendar
   cd ~/picalendar
   bash scripts/install.sh
   ```
   The installer sets up the backend service and writes the kiosk launcher
   to `~/.config/labwc/autostart`, including the screen rotation.
4. **Set her location** in `~/picalendar/config.json` (`latitude`,
   `longitude`, `timezone`, `location_label`).
5. **Remote access (strongly recommended — the Pi will be at her house):**
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up
   ```
   Now you can `ssh pi@momcal` from home and run `scripts/refresh.sh` or
   `scripts/kiosk.sh`.
6. **Dry run** with demo data: set `"fixtures": true` in `config.json`,
   `sudo systemctl restart picalendar`, `sudo reboot`. You should see the
   agenda (sideways, until the TV is rotated). Set `"fixtures": false` when
   you're done.

## 2. Connect her Google Calendar

This reuses your Google Cloud project. It's already **In production**, so
her Google account can authorize it. Google will warn that the app isn't
verified — click **Advanced → Go to piCalendar (unsafe)**. That's expected
for a personal app.

1. Copy your existing OAuth client file to her Pi:
   ```bash
   ssh pi@momcal mkdir -p /home/pi/.config/picalendar
   scp ~/.config/picalendar/credentials.json pi@momcal:/home/pi/.config/picalendar/
   ```
2. Sign in **as her**. Pick one:
   - **At the Pi** (keyboard attached, easiest before the TV is rotated):
     ```bash
     cd ~/picalendar && .venv/bin/python -m backend.oauth_init
     ```
     She signs in with her Google account and approves read-only calendar
     access.
   - **From your laptop**, if the Pi is already on the wall: move your own
     `~/.config/picalendar/token.json` aside, run
     `python -m backend.oauth_init` locally, let her sign in, then
     `scp ~/.config/picalendar/token.json pi@momcal:/home/pi/.config/picalendar/`
     and put your own token back.
3. Restart and check:
   ```bash
   sudo systemctl restart picalendar
   ~/picalendar/scripts/refresh.sh --hard
   ```
4. **Choosing calendars.** Every calendar in her Google Calendar list shows
   up, in its Google color. To add family calendars, share them with her
   account. To hide noise like Holidays or Birthdays, list only the ones you
   want in `config.json`:
   ```json
   "calendar_ids": ["her.email@gmail.com", "family-calendar-id@group.calendar.google.com"]
   ```
   Find each ID in Google Calendar → Settings → (calendar) → *Integrate
   calendar* → **Calendar ID**. Use `"hidden_titles"` to hide individual
   recurring events by title.
5. The token keeps working as long as the app stays in production and she
   doesn't revoke access. If the screen ever shows no events, repeat step 2.

## 3. Set up the TV

1. **Check the resolution** on the TV's label or spec sheet: 1080p
   (1920×1080) or 720p (1366×768 — common for 32" sets). The layout handles
   both; this just tells you what to expect.
2. **Mount it portrait**, top edge to the right. 31.5" TVs are usually VESA
   100×100 or 200×100. Check the manual's notes on portrait use and leave
   the vents clear. Route the HDMI and power so they don't bend hard at the
   ports.
3. **TV menu settings:**
   - Picture size / aspect: **Just Scan**, **Screen Fit**, or **Fit to
     Screen** (turns off overscan so the edges aren't cropped)
   - Turn off eco mode, auto power-off, and "no signal" sleep timers
   - Picture mode Standard or Calibrated; lower the brightness a little for
     a living room
   - Optional: turn on HDMI-CEC (Anynet+, Bravia Sync, SimpLink…) if you
     want the Pi to switch the TV on and off on a schedule later
4. **Rotation.** The installer adds
   `wlr-randr --output HDMI-A-1 --transform 90` to the kiosk autostart. If
   the picture comes up **upside down**, change `90` to `270` in
   `~/.config/labwc/autostart` (or rerun the installer with
   `ROTATION=270 bash scripts/install.sh` on a fresh autostart) and reboot.
   You can also try it live from the Pi's desktop: Control Centre →
   **Screens** → right-click the HDMI output → **Orientation**.
5. **Check it from your laptop.** Open `http://momcal:9222` (Chromium
   DevTools) and run `innerWidth + "x" + innerHeight` in the console. It
   should say about `1080x1920` (or `768x1366`).
6. **If it stutters**, the app switches itself to a lighter glass mode
   when the first frames are slow. You can confirm with
   `document.documentElement.dataset.perf` in DevTools (`"lite"` means it
   switched).

## Everyday fixes (over SSH)

| Problem | Fix |
| --- | --- |
| New event not showing yet | `~/picalendar/scripts/refresh.sh --hard` |
| Screen frozen or blank | `~/picalendar/scripts/kiosk.sh restart` |
| No events at all | Re-run the sign-in (section 2, step 2) |
| Backend errors | `journalctl -u picalendar -n 50` |
| Update the app | `cd ~/picalendar && git pull && sudo systemctl restart picalendar && scripts/refresh.sh --hard` |
