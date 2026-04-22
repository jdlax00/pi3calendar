"""Google Calendar integration — local OAuth flow, token refresh, merged fetch.

First-time setup is driven by backend/oauth_init.py; at runtime this module
reads the persisted token, refreshes as needed, and returns a flat, color-
annotated list of events across every calendar the account can see.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .cache import ttl_cache


SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

CONFIG_DIR = Path(os.path.expanduser("~/.config/picalendar"))
TOKEN_PATH = CONFIG_DIR / "token.json"
CREDENTIALS_PATH = CONFIG_DIR / "credentials.json"


def _load_credentials() -> Credentials:
    if not TOKEN_PATH.exists():
        raise RuntimeError(
            f"No Google token at {TOKEN_PATH}. Run `python -m backend.oauth_init` first."
        )
    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_PATH.write_text(creds.to_json())
    return creds


def _service():
    return build("calendar", "v3", credentials=_load_credentials(), cache_discovery=False)


@ttl_cache(ttl_seconds=5 * 60)
def list_all_events(start_iso: str, end_iso: str) -> list[dict]:
    svc = _service()

    calendars: list[dict] = []
    page_token = None
    while True:
        resp = svc.calendarList().list(pageToken=page_token).execute()
        calendars.extend(resp.get("items", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    events: list[dict] = []
    for cal in calendars:
        cal_id = cal["id"]
        cal_name = cal.get("summaryOverride") or cal.get("summary", cal_id)
        cal_color = cal.get("backgroundColor", "#888888")

        page_token = None
        while True:
            resp = svc.events().list(
                calendarId=cal_id,
                timeMin=start_iso,
                timeMax=end_iso,
                singleEvents=True,
                orderBy="startTime",
                pageToken=page_token,
                maxResults=250,
            ).execute()
            for ev in resp.get("items", []):
                normalized = _normalize_event(ev, cal_name, cal_color)
                if normalized is not None:
                    events.append(normalized)
            page_token = resp.get("nextPageToken")
            if not page_token:
                break

    events.sort(key=lambda e: e["start"])
    return events


def _normalize_event(ev: dict, cal_name: str, cal_color: str) -> dict | None:
    start = ev.get("start", {})
    end = ev.get("end", {})

    if "dateTime" not in start and "date" not in start:
        return None  # skip events with no usable start
    if "dateTime" not in end and "date" not in end:
        return None

    # Common fields for the event-detail popup. We render only what's present
    # so empty strings / empty lists are harmless on the frontend.
    organizer = ev.get("organizer") or {}
    attendees = ev.get("attendees") or []
    extras = {
        "description": ev.get("description", "") or "",
        "html_link": ev.get("htmlLink", "") or "",
        "organizer": organizer.get("displayName") or organizer.get("email") or "",
        "attendees": [
            (a.get("displayName") or a.get("email") or "")
            for a in attendees
            if not a.get("self")  # skip the viewer themselves — less noise in the popup
        ],
    }

    if "dateTime" in start and "dateTime" in end:
        return {
            "id": ev.get("id"),
            "title": ev.get("summary", "(Untitled)"),
            "calendar": cal_name,
            "color": cal_color,
            "start": start["dateTime"],
            "end": end["dateTime"],
            "all_day": False,
            "location": ev.get("location", "") or "",
            **extras,
        }
    if "date" in start and "date" in end:
        return {
            "id": ev.get("id"),
            "title": ev.get("summary", "(Untitled)"),
            "calendar": cal_name,
            "color": cal_color,
            "start": start["date"],
            "end": end["date"],
            "all_day": True,
            "location": ev.get("location", "") or "",
            **extras,
        }
    return None


def has_valid_token() -> bool:
    return TOKEN_PATH.exists()
