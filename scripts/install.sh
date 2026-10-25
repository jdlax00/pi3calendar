#!/usr/bin/env bash
#
# piCalendar installer — run on a fresh Raspberry Pi OS (Bookworm) install.
#
# Assumes the repo is cloned at /home/pi/picalendar.
#
set -euo pipefail

REPO_DIR="${REPO_DIR:-/home/pi/picalendar}"
USER_NAME="${USER_NAME:-pi}"
CONFIG_DIR="/home/${USER_NAME}/.config/picalendar"
AUTOSTART="/home/${USER_NAME}/.config/lxsession/LXDE-pi/autostart"
LABWC_AUTOSTART="/home/${USER_NAME}/.config/labwc/autostart"
# mom-vertical: output rotation for a TV mounted portrait. 90 or 270 —
# whichever makes the picture upright (see MOM_SETUP.md, "Set up the TV").
ROTATION="${ROTATION:-90}"
HDMI_OUTPUT="${HDMI_OUTPUT:-HDMI-A-1}"

echo "piCalendar install → ${REPO_DIR}"

if [[ ! -d "${REPO_DIR}" ]]; then
  echo "Repo not found at ${REPO_DIR}. Clone it there first." >&2
  exit 1
fi

# 1. System packages
echo "==> apt deps"
sudo apt-get update

# Chromium package name differs across Raspberry Pi OS releases:
#   Bookworm (Debian 12) and earlier → chromium-browser
#   Trixie   (Debian 13) and later   → chromium
CHROMIUM_PKG="chromium"
if ! apt-cache show chromium >/dev/null 2>&1; then
  CHROMIUM_PKG="chromium-browser"
fi

sudo apt-get install -y \
  python3 python3-venv python3-pip \
  "${CHROMIUM_PKG}" unclutter xdotool x11-xserver-utils wlr-randr

# 2. Python virtualenv
echo "==> venv + pip deps"
python3 -m venv "${REPO_DIR}/.venv"
"${REPO_DIR}/.venv/bin/pip" install --upgrade pip
"${REPO_DIR}/.venv/bin/pip" install -r "${REPO_DIR}/requirements.txt"

# 3. Config skeleton
echo "==> config dir"
mkdir -p "${CONFIG_DIR}"
if [[ ! -f "${REPO_DIR}/config.json" ]]; then
  cp "${REPO_DIR}/config.example.json" "${REPO_DIR}/config.json"
  echo "    created config.json from example — edit lat/lon before running"
fi

# 4. systemd unit
echo "==> systemd"
sudo cp "${REPO_DIR}/scripts/picalendar.service" /etc/systemd/system/picalendar.service
sudo sed -i "s|/home/pi/picalendar|${REPO_DIR}|g" /etc/systemd/system/picalendar.service
sudo sed -i "s|User=pi|User=${USER_NAME}|; s|Group=pi|Group=${USER_NAME}|" /etc/systemd/system/picalendar.service
sudo systemctl daemon-reload
sudo systemctl enable picalendar.service

# 5. Chromium kiosk autostart
echo "==> kiosk autostart"

# Current Raspberry Pi OS runs the labwc Wayland compositor on the Pi 3, and
# scripts/kiosk.sh drives ~/.config/labwc/autostart. labwc's autostart is a
# plain shell script (kiosk.sh runs it with bash), not LXDE's @-prefixed list.
if command -v labwc >/dev/null 2>&1; then
  mkdir -p "$(dirname "${LABWC_AUTOSTART}")"
  if [[ -f "${LABWC_AUTOSTART}" ]] && grep -q "picalendar kiosk" "${LABWC_AUTOSTART}"; then
    echo "    labwc autostart already has the kiosk — leaving it alone"
  else
    cat >> "${LABWC_AUTOSTART}" <<LABWC

# picalendar kiosk (mom-vertical: portrait)
wlr-randr --output ${HDMI_OUTPUT} --transform ${ROTATION}
${CHROMIUM_PKG} \\
  --kiosk \\
  --noerrdialogs \\
  --disable-infobars \\
  --disable-translate \\
  --disable-pinch \\
  --overscroll-history-navigation=0 \\
  --check-for-update-interval=604800 \\
  --enable-gpu-rasterization \\
  --ignore-gpu-blocklist \\
  --enable-zero-copy \\
  --remote-debugging-port=9222 \\
  http://localhost:5000 &
LABWC
    echo "    wrote ${LABWC_AUTOSTART} (rotation ${ROTATION} on ${HDMI_OUTPUT})"
  fi
fi

mkdir -p "$(dirname "${AUTOSTART}")"
touch "${AUTOSTART}"
if ! grep -q "picalendar kiosk" "${AUTOSTART}"; then
  echo "" >> "${AUTOSTART}"
  echo "# picalendar kiosk" >> "${AUTOSTART}"
  # Rewrite the @chromium line to whichever binary is actually installed.
  sed "s|^@chromium |@${CHROMIUM_PKG} |" \
    "${REPO_DIR}/scripts/kiosk-autostart" >> "${AUTOSTART}"
  # X11 fallback for the same portrait mount (90 → left, 270 → right).
  XR_ROT="left"; [[ "${ROTATION}" == "270" ]] && XR_ROT="right"
  echo "@xrandr --output HDMI-1 --rotate ${XR_ROT}" >> "${AUTOSTART}"
fi

echo
echo "Done."
echo
echo "Next steps:"
echo "  1. Edit ${REPO_DIR}/config.json — set latitude, longitude, timezone."
echo "  2. Drop your Google Desktop-app OAuth JSON at ${CONFIG_DIR}/credentials.json."
echo "     (https://console.cloud.google.com/apis/credentials)"
echo "  3. Run one-time OAuth:  cd ${REPO_DIR} && .venv/bin/python -m backend.oauth_init"
echo "  4. Start the backend:   sudo systemctl start picalendar"
echo "  5. Reboot to launch kiosk:  sudo reboot"
