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


app = Flask(__name__, static_folder=None)


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
    return send_from_directory(FRONTEND, "index.html")


@app.get("/assets/<path:filename>")
def assets(filename: str):
    return send_from_directory(FRONTEND / "assets", filename)


@app.get("/styles.css")
def styles():
    return send_from_directory(FRONTEND, "styles.css")


@app.get("/app.js")
def appjs():
    return send_from_directory(FRONTEND, "app.js")


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


@app.get("/api/events")
def api_events():
    start = request.args.get("start")
    end = request.args.get("end")
    if not start or not end:
        now = datetime.now(timezone.utc)
        sunday = now - timedelta(days=(now.weekday() + 1) % 7)
        sunday = sunday.replace(hour=0, minute=0, second=0, microsecond=0)
        start = sunday.isoformat()
        end = (sunday + timedelta(days=7)).isoformat()

    cfg = load_config()
    if cfg.get("fixtures") or USE_FIXTURES:
        return jsonify({"events": fixtures.fixture_events(start)})

    from . import google_calendar
    return jsonify({"events": google_calendar.list_all_events(start, end)})


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
