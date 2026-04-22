#!/usr/bin/env bash
#
# Manage the Chromium kiosk from an SSH shell.
#
# Usage:
#   scripts/kiosk.sh stop        Kill the running kiosk (drops to the desktop)
#   scripts/kiosk.sh start       Relaunch the kiosk into the Pi's Wayland session
#   scripts/kiosk.sh restart     stop + start
#   scripts/kiosk.sh disable     Prevent kiosk from autostarting on next boot
#   scripts/kiosk.sh enable      Re-enable autostart
#   scripts/kiosk.sh status      Show current running/autostart state (default)
#
# The "start" path works by inheriting WAYLAND_DISPLAY / XDG_RUNTIME_DIR from
# the running labwc compositor, so the SSH-launched Chromium attaches to the
# same Wayland session that's on the TV.

set -euo pipefail

AUTOSTART="${HOME}/.config/labwc/autostart"
AUTOSTART_OFF="${AUTOSTART}.off"
CMD="${1:-status}"

is_running() {
  pgrep -f "chromium.*--kiosk" >/dev/null 2>&1
}

# Pull WAYLAND_DISPLAY + XDG_RUNTIME_DIR + DBUS_SESSION_BUS_ADDRESS out of
# the running labwc process, so a command launched from ssh attaches to it.
load_wayland_env() {
  local pid
  pid="$(pgrep -x labwc | head -n1 || true)"
  if [[ -z "${pid}" ]]; then
    echo "error: labwc is not running — is the Pi at the desktop?" >&2
    return 1
  fi
  # /proc/<pid>/environ is NUL-separated.
  while IFS= read -r -d '' line; do
    case "${line}" in
      WAYLAND_DISPLAY=*|XDG_RUNTIME_DIR=*|DBUS_SESSION_BUS_ADDRESS=*|DISPLAY=*)
        export "${line?}"
        ;;
    esac
  done < "/proc/${pid}/environ"
}

kiosk_stop() {
  if is_running; then
    echo "stopping kiosk..."
    pkill -f "chromium.*--kiosk" || true
    # Give it a second to actually exit.
    for _ in 1 2 3 4 5; do
      is_running || break
      sleep 0.5
    done
    if is_running; then
      echo "warn: kiosk still running, sending SIGKILL" >&2
      pkill -9 -f "chromium.*--kiosk" || true
    fi
    echo "kiosk stopped"
  else
    echo "kiosk not running"
  fi
}

kiosk_start() {
  if is_running; then
    echo "kiosk already running — use 'restart' to bounce it"
    return
  fi
  if [[ ! -f "${AUTOSTART}" ]]; then
    echo "error: no autostart file at ${AUTOSTART}" >&2
    if [[ -f "${AUTOSTART_OFF}" ]]; then
      echo "       (disabled — run '$0 enable' first)" >&2
    fi
    exit 1
  fi
  load_wayland_env
  echo "starting kiosk (WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-?})..."
  # nohup + detached stdio so this survives the ssh session ending.
  nohup bash "${AUTOSTART}" </dev/null >/dev/null 2>&1 &
  disown
  # Give chromium a few seconds to spawn.
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    is_running && break
    sleep 0.5
  done
  if is_running; then
    echo "kiosk started"
  else
    echo "error: kiosk didn't come up — check 'journalctl --user -b | tail -40'" >&2
    exit 1
  fi
}

kiosk_disable() {
  if [[ -f "${AUTOSTART}" ]]; then
    mv "${AUTOSTART}" "${AUTOSTART_OFF}"
    echo "autostart disabled (moved to ${AUTOSTART_OFF})"
    echo "next reboot will come up to the normal desktop"
  elif [[ -f "${AUTOSTART_OFF}" ]]; then
    echo "autostart already disabled"
  else
    echo "error: no autostart file found at ${AUTOSTART} or ${AUTOSTART_OFF}" >&2
    exit 1
  fi
}

kiosk_enable() {
  if [[ -f "${AUTOSTART_OFF}" ]]; then
    mv "${AUTOSTART_OFF}" "${AUTOSTART}"
    echo "autostart enabled"
    echo "next reboot will launch the kiosk"
  elif [[ -f "${AUTOSTART}" ]]; then
    echo "autostart already enabled"
  else
    echo "error: no autostart file found at ${AUTOSTART} or ${AUTOSTART_OFF}" >&2
    exit 1
  fi
}

kiosk_status() {
  if is_running; then
    local pid
    pid="$(pgrep -f 'chromium.*--kiosk' | head -n1)"
    echo "kiosk:     running (pid ${pid})"
  else
    echo "kiosk:     stopped"
  fi
  if [[ -f "${AUTOSTART}" ]]; then
    echo "autostart: enabled  (${AUTOSTART})"
  elif [[ -f "${AUTOSTART_OFF}" ]]; then
    echo "autostart: disabled (${AUTOSTART_OFF})"
  else
    echo "autostart: missing  (neither ${AUTOSTART} nor ${AUTOSTART_OFF} exists)"
  fi
  if systemctl is-active --quiet picalendar 2>/dev/null; then
    echo "backend:   active"
  else
    echo "backend:   $(systemctl is-active picalendar 2>/dev/null || echo unknown)"
  fi
}

case "${CMD}" in
  stop)    kiosk_stop ;;
  start)   kiosk_start ;;
  restart) kiosk_stop; sleep 1; kiosk_start ;;
  disable) kiosk_disable ;;
  enable)  kiosk_enable ;;
  status)  kiosk_status ;;
  -h|--help|help)
    sed -n '3,16p' "$0" | sed 's/^# \{0,1\}//'
    ;;
  *)
    echo "usage: $0 {stop|start|restart|disable|enable|status}" >&2
    exit 1
    ;;
esac
