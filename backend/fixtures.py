from datetime import datetime, timedelta


def _today_anchor(now: datetime) -> datetime:
    """Anchor the fixture week at the start of today so a full 7 days of
    events are always visible in the rolling today-first grid."""
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def fixture_events(start_iso: str | None = None, end_iso: str | None = None) -> list[dict]:
    """Hand-crafted 8 days (today + 7) spanning the 5 Google Calendars our family uses.

    The window args are accepted for signature parity with the Google
    fetcher; the fixture always covers the agenda's today-first 8 days.

    Timestamps are emitted in the host's local timezone so the fixture feels
    natural in the browser regardless of where the host sits. Day 0 = today.
    """
    now_local = datetime.now().astimezone()
    week_start = _today_anchor(now_local)

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

    # Day 0 (today)
    add(0, 9, 10.5, "Farmers market", "family", "Downtown")
    add(0, 14, 16, "Emma soccer practice", "kids", "Riverside Park")
    add(0, 18, 19.5, "Dinner @ Mom's", "family")

    # Day 1
    add(1, 8.5, 9, "Standup", "work")
    add(1, 10, 11, "1:1 with Priya", "work")
    add(1, 10.5, 11.5, "Design review", "work")  # overlaps
    add(1, 12.5, 13, "Dentist", "personal")
    add(1, 17, 18, "Piano lesson — Jack", "kids")

    # Day 2
    add(2, 9, 10, "Sprint planning", "work")
    add(2, 11, 12, "Quarterly review prep", "work")
    add(2, 15.5, 17, "Emma + Jack pickup", "kids")
    add(2, 19, 20.5, "Book club", "personal")
    # Crowded on purpose — exercises the agenda's "+N more" truncation.
    add(2, 7, 7.5, "Walk with Linda", "personal")
    add(2, 8, 8.5, "Pharmacy pickup", "personal")
    add(2, 12, 13, "Lunch w/ Carol", "family")
    add(2, 13.5, 14, "Call the plumber", "personal")
    add(2, 14, 15, "Hair appointment", "personal")
    add(2, 17, 18, "Grandkids' recital", "kids")
    add(2, 18, 19, "Choir practice", "personal")

    # Day 3
    add_allday(3, 1, "Anniversary", "birthdays")
    add(3, 7.5, 8, "Gym", "personal")
    add(3, 13, 14, "Lunch w/ Sam", "personal", "Oro")
    add(3, 18.5, 20.5, "Anniversary dinner", "personal", "Fiola")

    # Day 4
    add(4, 8.5, 9, "Standup", "work")
    add(4, 10, 11.5, "Design review — Loom project", "work")
    add(4, 11, 12, "Pediatrician — Jack", "kids")  # overlaps prior
    add(4, 15, 16, "Client call — Horizon", "work")

    # Day 5 — multi-day trip starts
    add_allday(5, 3, "Beach weekend", "family")
    add(5, 9, 10, "Wrap-up + handoff", "work")
    add(5, 11, 11.75, "Coffee w/ Alex", "personal")

    # Day 6
    add(6, 9, 10.5, "Morning run", "personal")
    add(6, 17, 19, "Beach dinner", "family")

    # Day 7 — last agenda day
    add(7, 9, 10.5, "Church", "family")
    add(7, 12, 13.5, "Sunday brunch", "family")

    return sorted(events, key=lambda e: e["start"])


def fixture_weather() -> dict:
    """Plausible early-spring 8-day forecast (today + 7), starting today."""
    week_start = _today_anchor(datetime.now().astimezone())
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
        (65, 47, 1),
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

    return {
        "current": {
            "temp_f": 68,
            "weather_code": 2,
            "description": "Partly cloudy",
        },
        "daily": daily,
        "sunrise_today": daily[0]["sunrise"],
        "sunset_today": daily[0]["sunset"],
    }
