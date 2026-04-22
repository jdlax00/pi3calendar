# Setting up the SD card for piCalendar

Step-by-step from a blank SD card to "ready to run `scripts/install.sh`".
Targeted at a Raspberry Pi 3 driving a Vizio TV over HDMI.

## What you need

- **Raspberry Pi 3** (any variant) + power supply + HDMI cable
- **microSD card, 16 GB or larger** (32 GB Class 10 / A1 recommended)
- **A computer with an SD card reader** (Mac, Windows, or Linux)
- **A USB keyboard + mouse** — needed briefly during first boot and OAuth.
  You can unplug them once the kiosk is running.
- **A network the Pi can reach** — wired Ethernet is easiest. Wi-Fi works too.

## 1. Flash Raspberry Pi OS to the SD card

1. Download **Raspberry Pi Imager** from https://www.raspberrypi.com/software
   and install it.
2. Insert the microSD card into your computer.
3. Open Raspberry Pi Imager and click **Choose Device** → **Raspberry Pi 3**.
4. Click **Choose OS** → **Raspberry Pi OS (other)** →
   **Raspberry Pi OS (64-bit) — A port of Debian Bookworm with the
   Raspberry Pi Desktop**. (The _Full_ variant is fine too; it's just
   larger. Avoid _Lite_ — we need the desktop environment for the
   Chromium kiosk.)
5. Click **Choose Storage** and pick your SD card. Double-check it's the
   right drive.
6. Click **Next** → **Edit Settings** (or **Would you like to apply OS
   customisation settings?** → **Edit Settings**). In that dialog:

   **General tab**
   - Set hostname: `picalendar`
   - Set username: `pi`, password: _(something you'll remember)_
   - Configure Wi-Fi SSID + password if you're not using Ethernet
   - Set locale / timezone / keyboard layout

   **Services tab**
   - Enable **SSH** → **Use password authentication**

   **Options tab**
   - Eject media when finished: on
   - Telemetry: off

7. Save → **Yes** to apply → **Yes** to overwrite the SD card.
8. Wait ~5 minutes for flash + verify. Eject.

## 2. First boot

1. Put the SD card in the Pi, plug in HDMI to the TV, USB keyboard +
   mouse, and Ethernet (or skip Ethernet if you configured Wi-Fi above).
2. Plug in power. First boot takes 2–3 minutes; the Pi will reboot once.
3. You should land on the Raspberry Pi OS desktop.
4. Open a terminal (top-left, the little black icon, or `Ctrl+Alt+T`).

## 3. Find the Pi's IP (optional — lets you SSH in instead of typing at the TV)

In the terminal on the Pi:

```bash
hostname -I
```

Copy that IP. From your laptop:

```bash
ssh pi@<that-ip>
```

From here on, I'll assume you're in a terminal on the Pi (either
directly or via SSH — both work the same).

## 4. Update the system

```bash
sudo apt update
sudo apt full-upgrade -y
sudo reboot
```

Wait for it to come back, then reconnect.

## 5. Make sure the display is actually 1080p

Easiest route: on the Pi desktop, **Raspberry Pi menu → Preferences →
Screen Configuration**. Make sure the TV reports `1920×1080` at 60 Hz.
If it doesn't, the Vizio may be defaulting to 720p — pick 1920×1080
and apply.

If you're headless over SSH, check what mode the HDMI is using:

```bash
tvservice -s    # shows current HDMI mode on Pi 3
```

Expected: `HDMI ... 1920x1080 @ 60.00Hz`. If it's something else, edit
`/boot/firmware/config.txt` and add:

```
hdmi_group=1
hdmi_mode=16   # 1080p @ 60Hz
```

Reboot.

## 6. Get the piCalendar code onto the Pi

```bash
cd ~
git clone <YOUR_REPO_URL> picalendar
```

If you don't have this in a git repo yet, the alternative is to copy it
over with `scp` from your laptop:

```bash
# on your laptop, from inside the piCalendar project directory:
scp -r . pi@<pi-ip>:~/picalendar
```

## 7. Create your Google OAuth credentials (do this on your laptop)

You only do this once per household. **Heads up:** Google rebranded the
OAuth consent flow to "Google Auth Platform" in 2024–25. The steps
below match the current UI. If Google moves things again, the rough
shape — _configure consent → publish → create a Desktop client_ — will
be the same.

### 7a. Create the project and enable the API

1. Go to https://console.cloud.google.com and sign in with the Google
   account whose calendars you want to see.
2. Project dropdown (top of page) → **New Project** → name it
   `picalendar` → **Create**. Make sure the dropdown now shows
   `picalendar` before continuing.
3. Left nav: **APIs & Services → Library** → search
   **Google Calendar API** → click it → **Enable**.

### 7b. Configure the consent screen (new "Google Auth Platform" wizard)

4. Left nav: **APIs & Services → OAuth consent screen**. You'll land on
   a page titled **Google Auth Platform** with a **Get Started** button.
   Click it. Four steps:
   1. **App Information** — App name: `piCalendar`, User support email:
      your email → Next
   2. **Audience** — **External** → Next
   3. **Contact Information** — your email → Next
   4. **Finish** — check _I agree to the User Data Policy_ →
      **Continue** → **Create**

   You now see a dashboard with left-nav tabs: Overview, Branding,
   Audience, Clients, Data Access, Verification Center.

### 7c. Publish the app

Why: in _Testing_ mode Google revokes your refresh token after 7 days.
For an always-on display you want _In production_.

5. Click the **Audience** tab. At the top you'll see:

   > Publishing status: **Testing**
   > User type: External
   > [ Publish app ]

   Click **Publish app** → **Confirm**. Status flips to **In production**.

   Your app will be unverified — that's fine for personal use. When you
   sign in during OAuth (step 10 in this guide), Google will warn
   _"Google hasn't verified this app."_ Click **Advanced → Go to
   piCalendar (unsafe)** once and you're through.

### 7d. Create the Desktop OAuth client

6. Still in Google Auth Platform, click the **Clients** tab →
   **+ Create Client**. (Equivalent path: _APIs & Services → Credentials
   → + Create Credentials → OAuth client ID_.)
   - Application type: **Desktop app**
   - Name: `picalendar-pi`
   - **Create**

7. A dialog shows the new client ID. Click **Download JSON** (cloud-
   download icon). You get `client_secret_XXXXXX.json` in your
   Downloads folder.

### 7e. Copy the credentials to the Pi

```bash
# on the Pi first:
mkdir -p ~/.config/picalendar

# then on your laptop:
scp ~/Downloads/client_secret_*.json \
    pi@<pi-ip>:/home/pi/.config/picalendar/credentials.json
```

## 8. Edit `config.json`

On the Pi:

```bash
cd ~/picalendar
cp config.example.json config.json
nano config.json
```

Set:
- `latitude` and `longitude` — look up your address on
  https://www.latlong.net (or just Google "my lat long")
- `timezone` — IANA name, e.g. `America/New_York`,
  `America/Los_Angeles`, `America/Chicago`
- `location_label` — whatever string you want in the header
  (`"Washington, DC"`, `"Home"`, etc.)

Save (`Ctrl+O`, Enter, `Ctrl+X`).

## 9. Run the installer

```bash
cd ~/picalendar
bash scripts/install.sh
```

This:
- Installs Chromium, unclutter, Python venv, and the pip deps
- Creates the systemd service and enables it on boot
- Appends the Chromium kiosk launcher to your LXDE autostart

## 10. Authorize Google once (keyboard must be attached)

Still on the Pi:

```bash
cd ~/picalendar
.venv/bin/python -m backend.oauth_init
```

A Chromium window opens to Google's consent screen → sign in with the
Google account you used in step 7 → approve `piCalendar` → the window
says "The authentication flow has completed". Close it. A
`token.json` is now sitting in `~/.config/picalendar/` and you never
need to do this again.

## 11. Start it and reboot

```bash
sudo systemctl start picalendar
sudo systemctl status picalendar    # should say "active (running)"
curl -s http://localhost:5000/api/weather | head -c 200    # smoke test
sudo reboot
```

On the reboot, the Pi will boot straight into the Chromium kiosk pointed
at `http://localhost:5000`. Unplug the keyboard and mouse, and you're
done.

## If anything goes wrong

**Black screen after reboot.** Re-plug a keyboard, press `Alt+F2` to get
a shell. Check:
```bash
systemctl status picalendar
journalctl -u picalendar -n 50
```

**Calendar empty.** Token may be missing or expired. Re-run
`python -m backend.oauth_init`.

**Glass looks pixelated or janky.** Open DevTools remotely from your
laptop on the LAN: `http://<pi-ip>:9222`. Rendering → _Highlight layers_.
Each glass surface should be on its own GPU layer. If not, double-check
that `/etc/xdg/lxsession/LXDE-pi/autostart` (or `~/.config/lxsession/
LXDE-pi/autostart`) contains `--ignore-gpu-blocklist --use-gl=egl`. The
frontend will also automatically flip `data-perf="lite"` if frame times
are bad.

**Hide the mouse cursor.** `unclutter` is installed by the installer
and launches automatically. If the cursor still appears, confirm
`@unclutter -idle 0` is in the autostart file.
