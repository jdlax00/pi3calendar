# Mom's vertical calendar — setup

Raspberry Pi 3B+ driving a 31.5" TV mounted **portrait, rotated clockwise
(the TV's top edge goes to the right)**. This branch (`mom-vertical`) shows
an agenda: a big Today card plus the next 7 days, each with its weather.

Do it in this order: boot the Pi at your place → dry run with demo data →
connect her calendar → mount and rotate the TV at her house.

## Progress

- [x] Flash the SD card (Imager: hostname `momcal`, her Wi-Fi, SSH with
      your Mac's public key, Raspberry Pi Connect on)
- [ ] First boot + update — **you are here**
- [ ] Install the app from this branch
- [ ] Set her location in `config.json`
- [ ] Dry run with demo data
- [ ] Connect her Google Calendar
- [ ] Mount and rotate the TV at her house

---

## 1. Boot the Pi

What you need: Pi 3B+, the official **5.1V 2.5A** micro-USB power supply
(underpowered supplies cause throttling and Chromium crashes), a 16–32 GB
microSD card, HDMI cable, USB keyboard + mouse for setup.

1. ✅ **Flash the card** with Raspberry Pi Imager (done):
   - Device: **Raspberry Pi 3**
   - OS: **Raspberry Pi OS (64-bit)** — the desktop version, not Lite
   - Edit settings:
     - Hostname `momcal`, username `pi`, a password (used for `sudo` and
       the desktop — SSH won't accept it)
     - Wi-Fi: **her** network name and password (or plan on Ethernet)
     - Locale/timezone: hers (e.g. `America/Denver`)
     - Services: **SSH with public-key authentication only**, using your
       Mac's `~/.ssh/id_ed25519.pub`
     - **Raspberry Pi Connect** on, signed in with your Raspberry Pi ID
   - If the card doesn't appear in Imager: check the lock switch on the
     card's edge (macOS reports it as read-only), then restart Imager.
2. **First boot** on any screen, landscape is fine. Put the card in the Pi,
   connect HDMI, keyboard, and mouse, then plug in power **last**. First
   boot takes 2–5 minutes and may reboot once.

   If you used **her** Wi-Fi in Imager and you're at your place, the Pi
   won't get online. Join your Wi-Fi from the network icon in the top bar
   (it remembers both), or plug in Ethernet.

   Then open a terminal (or SSH in from your Mac with `ssh pi@momcal.local`)
   and update:
   ```bash
   sudo apt update && sudo apt full-upgrade -y && sudo reboot
   ```
   Once it's back, confirm it shows up at https://connect.raspberrypi.com.
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
5. **Remote access** is covered by **Raspberry Pi Connect**: from anywhere,
   open https://connect.raspberrypi.com → `momcal` → **Remote shell**, then
   run `scripts/refresh.sh` or `scripts/kiosk.sh`. No router setup needed.

   Optional: Tailscale. Connect is a browser terminal only. If you also want
   `ssh`/`scp` from your Mac or the remote DevTools at `:9222` while the Pi
   is at her house, install Tailscale (https://tailscale.com/download) on
   both the Pi and your Mac:
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up
   ```
6. **Dry run** with demo data: set `"fixtures": true` in `config.json`,
   `sudo systemctl restart picalendar`, `sudo reboot`. You should see the
   agenda (sideways, until the TV is rotated). Set `"fixtures": false` when
   you're done.

## 2. Connect her Google Calendar

This reuses your Google Cloud project. It's already **In production**, so
her Google account can authorize it. Google will warn that the app isn't
verified — click **Advanced → Go to piCalendar (unsafe)**. That's expected
for a personal app.

1. Copy your existing OAuth client file to her Pi. Do this **while the Pi
   is still on your network** (these use `momcal.local`, which only resolves
   on the same Wi-Fi):
   ```bash
   ssh pi@momcal.local mkdir -p /home/pi/.config/picalendar
   scp ~/.config/picalendar/credentials.json pi@momcal.local:/home/pi/.config/picalendar/
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
     `python -m backend.oauth_init` locally, let her sign in, then copy the
     token over. Without Tailscale, `scp` only works on the same network;
     otherwise paste the file's contents into
     `~/.config/picalendar/token.json` from Connect's remote shell. Put your
     own token back afterward.
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
5. **Check it from your laptop** on her Wi-Fi (or over Tailscale). Open
   `http://momcal.local:9222` (Chromium DevTools) and run `innerWidth + "x" + innerHeight` in the console. It
   should say about `1080x1920` (or `768x1366`).
6. **If it stutters**, the app switches itself to a lighter glass mode
   when the first frames are slow. You can confirm with
   `document.documentElement.dataset.perf` in DevTools (`"lite"` means it
   switched).

## Everyday fixes (Connect remote shell, or SSH)

| Problem | Fix |
| --- | --- |
| New event not showing yet | `~/picalendar/scripts/refresh.sh --hard` |
| Screen frozen or blank | `~/picalendar/scripts/kiosk.sh restart` |
| No events at all | Re-run the sign-in (section 2, step 2) |
| Backend errors | `journalctl -u picalendar -n 50` |
| Update the app | `cd ~/picalendar && git pull && sudo systemctl restart picalendar && scripts/refresh.sh --hard` |
