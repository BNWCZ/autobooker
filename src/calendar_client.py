import os
from datetime import date, datetime, timedelta

import pytz
from google.oauth2 import service_account
from googleapiclient.discovery import build

PARIS_TZ = pytz.timezone("Europe/Paris")
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")
SERVICE_ACCOUNT_PATH = os.getenv("GOOGLE_SERVICE_ACCOUNT_PATH", "service_account.json")


def _service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_PATH, scopes=SCOPES
    )
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def _events_for_range(start: date, end: date) -> list:
    time_min = PARIS_TZ.localize(datetime(start.year, start.month, start.day, 0, 0, 0)).isoformat()
    time_max = PARIS_TZ.localize(datetime(end.year, end.month, end.day, 23, 59, 59)).isoformat()

    result = _service().events().list(
        calendarId=CALENDAR_ID,
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy="startTime",
        timeZone="Europe/Paris",
    ).execute()

    return result.get("items", [])


def _is_btt(event: dict) -> bool:
    return event.get("summary", "").strip().upper() == "BTT"


def has_btt_event(target_date: date) -> bool:
    """Returns True if there is a BTT event on target_date."""
    events = _events_for_range(target_date, target_date)
    return any(_is_btt(e) for e in events)


def has_btt_events_next_week(today: date) -> bool:
    """Returns True if next Mon–Fri has at least one BTT event.
    today should be Saturday or Sunday.
    """
    days_to_monday = 7 - today.weekday()  # Sat→2, Sun→1
    monday = today + timedelta(days=days_to_monday)
    friday = monday + timedelta(days=4)

    events = _events_for_range(monday, friday)
    return any(_is_btt(e) for e in events)
