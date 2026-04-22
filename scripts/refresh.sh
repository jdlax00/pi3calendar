#!/usr/bin/env bash
#
# Refresh the piCalendar dashboard from an SSH shell.
#
# Default:   restart the backend so the events/weather cache is cleared.
#            The frontend picks up new data on its next poll (up to ~5 min).
#
# --hard:    ALSO force the running Chromium kiosk to reload immediately,
#            via its remote debugging port. Use this when you added a test
#            event in Google Calendar and want it visible right now.
#
# Usage:
#   scripts/refresh.sh
#   scripts/refresh.sh --hard

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HARD=0

for arg in "$@"; do
  case "${arg}" in
    --hard|-f|--force) HARD=1 ;;
    -h|--help)
      sed -n '3,14p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) echo "usage: $0 [--hard]" >&2; exit 1 ;;
  esac
done

echo "==> restarting backend (clears 5-min events + 30-min weather cache)"
sudo systemctl restart picalendar

# Wait for the service to start answering again before returning.
for _ in $(seq 1 20); do
  if curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/api/config 2>/dev/null | grep -q "200"; then
    echo "    backend is up"
    break
  fi
  sleep 0.25
done

if [[ "${HARD}" -eq 1 ]]; then
  echo "==> reloading the kiosk browser via CDP (port 9222)"
  if ! curl -s -o /dev/null http://localhost:9222/json; then
    echo "    error: Chromium remote debugging port 9222 is not responding" >&2
    echo "           is the kiosk running? ('scripts/kiosk.sh status')" >&2
    exit 1
  fi
  PY="${REPO_DIR}/.venv/bin/python"
  if [[ ! -x "${PY}" ]]; then
    PY="$(command -v python3)"
  fi
  "${PY}" "${REPO_DIR}/scripts/cdp_reload.py"
else
  echo "==> done. frontend will auto-poll within ~5 min."
  echo "    (use --hard to force an immediate browser reload)"
fi
