from datetime import datetime, timedelta, timezone


def _sunday_anchor(now: datetime) -> datetime:
    # weekday(): Mon=0..Sun=6. We want Sunday-anchored weeks, so offset is (weekday+1)%7.
    start = now - timedelta(days=(now.weekday() + 1) % 7)
    return start.replace(hour=0, minute=0, second=0, microsecond=0)


def fixture_events(start_iso: str | None = None) -> list[dict]:
    """Hand-crafted week of events spanning the 5 Google Calendars our family uses.

    Timestamps are emitted in the host's local timezone so the fixture feels
    natural in the browser regardless of where the host sits.
    """
    now_local = datetime.now().astimezone()
    week_start = _sunday_anchor(now_local)

    def at(day: int, hour: int, minute: int = 0) -> str:
        return (week_start + timedelta(days=day, hours=hour, minutes=minute)).isoformat()

    def allday(day: int, span_days: int = 1) -> tuple[str, str]:
        s = (week_start + timedelta(days=day)).date().isoformat()
        e = (week_start + timedelta(days=day + span_days)).date().isoformat()
        return s, e

    cals = {
        "personal": "#b8754a",
        "work": "#4a6fa5",
        "family": "#7a9b5f",
        "kids": "#c58a9b",
        "birthdays": "#d1b464",
    }

    events: list[dict] = []

    def add(day, start_h, end_h, title, cal, location=""):
        events.append({
            "id": f"e{len(events)}",
            "title": title,
            "calendar": cal,
            "color": cals[cal],
            "start": at(day, int(start_h), int((start_h % 1) * 60)),
            "end": at(day, int(end_h), int((end_h % 1) * 60)),
            "all_day": False,
            "location": location,
        })

    def add_allday(day, span, title, cal):
        s, e = allday(day, span)
        events.append({
            "id": f"e{len(events)}",
            "title": title,
            "calendar": cal,
            "color": cals[cal],
            "start": s,
            "end": e,
            "all_day": True,
            "location": "",
        })

    # Sunday
    add(0, 9, 10.5, "Farmers market", "family", "Downtown")
    add(0, 14, 16, "Emma soccer practice", "kids", "Riverside Park")
    add(0, 18, 19.5, "Sunday dinner @ Mom's", "family")

    # Monday
    add(1, 8.5, 9, "Standup", "work")
    add(1, 10, 11, "1:1 with Priya", "work")
    add(1, 10.5, 11.5, "Design review", "work")  # overlaps
    add(1, 12.5, 13, "Dentist", "personal")
    add(1, 17, 18, "Piano lesson — Jack", "kids")

    # Tuesday
    add(2, 9, 10, "Sprint planning", "work")
    add(2, 11, 12, "Quarterly review prep", "work")
    add(2, 15.5, 17, "Emma + Jack pickup", "kids")
    add(2, 19, 20.5, "Book club", "personal")

    # Wednesday
    add_allday(3, 1, "Anniversary", "birthdays")
    add(3, 7, 8, "Gym", "personal")
    add(3, 13, 14, "Lunch w/ Sam", "personal", "Oro")
    add(3, 18.5, 21, "Anniversary dinner", "personal", "Fiola")

    # Thursday
    add(4, 8.5, 9, "Standup", "work")
    add(4, 10, 11.5, "Design review — Loom project", "work")
    add(4, 11, 12, "Pediatrician — Jack", "kids")  # overlaps prior
    add(4, 15, 16, "Client call — Horizon", "work")

    # Friday — multi-day trip starts
    add_allday(5, 3, "Beach weekend", "family")
    add(5, 9, 10, "Wrap-up + handoff", "work")
    add(5, 11, 11.75, "Coffee w/ Alex", "personal")

    # Saturday
    add(6, 9, 10.5, "Morning run", "personal")
    add(6, 17, 19, "Beach dinner", "family")

    return sorted(events, key=lambda e: e["start"])


def fixture_weather() -> dict:
    """Plausible early-spring 7-day forecast."""
    week_start = _sunday_anchor(datetime.now().astimezone())
    # WMO codes: 0 clear, 1 mainly clear, 2 partly cloudy, 3 overcast,
    # 45/48 fog, 51/53/55 drizzle, 61/63/65 rain, 71/73/75 snow, 95 thunder
    daily = []
    samples = [
        (66, 48, 2),
        (71, 50, 1),
        (74, 53, 0),
        (69, 51, 3),
        (63, 49, 61),
        (58, 46, 63),
        (62, 48, 2),
    ]
    for i, (hi, lo, code) in enumerate(samples):
        day = (week_start + timedelta(days=i))
        sunrise = day.replace(hour=6, minute=38)
        sunset = day.replace(hour=19, minute=52)
        daily.append({
            "date": day.date().isoformat(),
            "high_f": hi,
            "low_f": lo,
            "weather_code": code,
            "sunrise": sunrise.isoformat(),
            "sunset": sunset.isoformat(),
        })

    now = datetime.now(timezone.utc)
    today_index = min(6, max(0, (now - week_start).days))
    return {
        "current": {
            "temp_f": 68,
            "weather_code": 2,
            "description": "Partly cloudy",
        },
        "daily": daily,
        "sunrise_today": daily[today_index]["sunrise"],
        "sunset_today": daily[today_index]["sunset"],
    }
