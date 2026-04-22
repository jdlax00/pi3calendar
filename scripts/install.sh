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

echo "piCalendar install → ${REPO_DIR}"

if [[ ! -d "${REPO_DIR}" ]]; then
  echo "Repo not found at ${REPO_DIR}. Clone it there first." >&2
  exit 1
fi

# 1. System packages
echo "==> apt deps"
sudo apt-get update
sudo apt-get install -y \
  python3 python3-venv python3-pip \
  chromium-browser unclutter xdotool

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
mkdir -p "$(dirname "${AUTOSTART}")"
touch "${AUTOSTART}"
if ! grep -q "picalendar kiosk" "${AUTOSTART}"; then
  echo "" >> "${AUTOSTART}"
  echo "# picalendar kiosk" >> "${AUTOSTART}"
  cat "${REPO_DIR}/scripts/kiosk-autostart" >> "${AUTOSTART}"
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
