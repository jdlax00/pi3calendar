from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from . import fixtures

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
CONFIG_PATH = Path(os.environ.get("PICAL_CONFIG", ROOT / "config.json"))

USE_FIXTURES = os.environ.get("PICAL_FIXTURES", "") == "1"

# Events whose title contains any of these substrings (case-insensitive) are
# filtered out before being sent to the client. Useful for hiding noisy
# recurring meetings the family doesn't want on the living-room display.
HIDDEN_TITLE_SUBSTRINGS = ("wildebeast",)


app = Flask(__name__, static_folder=None)


def _no_store(response):
    """Tell the browser never to cache the frontend bundle.

    Flask's default SEND_FILE_MAX_AGE_DEFAULT is 12h, which means Chromium
    keeps serving the old app.js/styles.css across normal reloads — the
    dashboard only picks up new code on a hard refresh (Ctrl+Shift+R or our
    CDP `ignoreCache: true` path). These files are tiny and served from
    localhost, so no-store costs nothing and keeps the kiosk's 3 AM reload
    (and any normal refresh) honest after a deploy.
    """
    response.headers["Cache-Control"] = "no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {
        "latitude": 38.8977,
        "longitude": -77.0365,
        "timezone": "America/New_York",
        "location_label": "Home",
        "fixtures": USE_FIXTURES,
    }


@app.get("/")
def index():
    return _no_store(send_from_directory(FRONTEND, "index.html"))


@app.get("/assets/<path:filename>")
def assets(filename: str):
    # Fonts and background images are versioned-by-filename and ~stable, so
    # let the browser cache them normally. Only the HTML/JS/CSS bundle needs
    # the no-store treatment.
    return send_from_directory(FRONTEND / "assets", filename)


@app.get("/styles.css")
def styles():
    return _no_store(send_from_directory(FRONTEND, "styles.css"))


@app.get("/app.js")
def appjs():
    return _no_store(send_from_directory(FRONTEND, "app.js"))


@app.get("/api/config")
def api_config():
    cfg = load_config()
    return jsonify({
        "latitude": cfg["latitude"],
        "longitude": cfg["longitude"],
        "timezone": cfg.get("timezone", "UTC"),
        "location_label": cfg.get("location_label", ""),
        "fixtures": bool(cfg.get("fixtures") or USE_FIXTURES),
        "theme_override": cfg.get("theme_override"),  # "day" | "night" | null
    })


def _filter_hidden(events: list[dict]) -> list[dict]:
    """Strip out events whose title matches any HIDDEN_TITLE_SUBSTRINGS."""
    if not HIDDEN_TITLE_SUBSTRINGS:
        return events
    needles = tuple(s.lower() for s in HIDDEN_TITLE_SUBSTRINGS)
    return [
        e for e in events
        if not any(n in (e.get("title") or "").lower() for n in needles)
    ]


@app.get("/api/events")
def api_events():
    start = request.args.get("start")
    end = request.args.get("end")
    if not start or not end:
        # Fallback if the client didn't pass a window — today through +7 days.
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        start = today.isoformat()
        end = (today + timedelta(days=7)).isoformat()

    cfg = load_config()
    if cfg.get("fixtures") or USE_FIXTURES:
        return jsonify({"events": _filter_hidden(fixtures.fixture_events(start))})

    from . import google_calendar
    return jsonify({"events": _filter_hidden(google_calendar.list_all_events(start, end))})


@app.get("/api/weather")
def api_weather():
    cfg = load_config()
    if cfg.get("fixtures") or USE_FIXTURES:
        return jsonify(fixtures.fixture_weather())

    from . import weather
    return jsonify(weather.fetch_weather(
        cfg["latitude"], cfg["longitude"], cfg.get("timezone", "auto")
    ))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=False)
