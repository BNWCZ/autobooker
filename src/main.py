import csv
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytz
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

from auth import ensure_authenticated, get_browser_context, save_session
from booker import book, cancel, checkin
from calendar_client import has_remote_events_next_week, get_ooo_calendar_days
from discord_commands import SKIP, check_skip_commands
from notifier import notify

PARIS_TZ = pytz.timezone("Europe/Paris")
APP_URL = os.getenv("APP_URL", "https://doorjames.app")
BOOKINGS_PATH = Path(os.getenv("BOOKINGS_PATH", "bookings.csv"))

DAYS_AHEAD = 41

_SILENT_OOO_STATUSES = ("out of office - holidays", "out of office - public holiday")


def _is_silent_day() -> bool:
    """Return True on days where notifications should be silent: weekends, public holidays, calendar holidays."""
    import holidays as holidays_lib
    today = datetime.now(PARIS_TZ).date()
    if today.weekday() >= 5:
        return True
    if today in holidays_lib.France():
        return True
    status = _load_bookings().get(today.isoformat(), "")
    return status in _SILENT_OOO_STATUSES


# ---------------------------------------------------------------------------
# bookings.csv helpers
# ---------------------------------------------------------------------------

def _load_bookings() -> dict[str, str]:
    if not BOOKINGS_PATH.exists():
        return {}
    with open(BOOKINGS_PATH, newline="") as f:
        return {row["date"]: row["status"] for row in csv.DictReader(f)}


def _save_bookings(bookings: dict[str, str]) -> None:
    with open(BOOKINGS_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "status"])
        for d in sorted(bookings):
            writer.writerow([d, bookings[d]])


def _update_status(date_str: str, status: str) -> None:
    bookings = _load_bookings()
    bookings[date_str] = status
    _save_bookings(bookings)


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------

def run_book() -> None:
    now = datetime.now(PARIS_TZ)
    target = (now + timedelta(days=DAYS_AHEAD)).date()
    target_str = target.isoformat()

    if target.weekday() >= 5:
        print(f"[book] {target_str} is a weekend — skipping.")
        return

    existing = _load_bookings().get(target_str, "")
    if existing in ("booked", "checked_in") or existing.startswith("out of office"):
        print(f"[book] {target_str} already has status '{existing}' — skipping.")
        return

    with sync_playwright() as p:
        browser, context = get_browser_context(p, headless=True)
        page = context.new_page()
        try:
            page.goto(APP_URL)
            page.wait_for_load_state("load")

            if ensure_authenticated(page, context):
                notify("Réauthentification réussie ✅", "Session renouvelée automatiquement", silent=_is_silent_day())

            book(page, target)
            _update_status(target_str, "booked")
            notify("Réservation réussie ✅", f"Bureau réservé pour le {target_str} (09:00–17:00)", silent=_is_silent_day())

        except Exception as e:
            _update_status(target_str, "error")
            notify("Erreur réservation ❌", f"{target_str} — {e}")
            raise
        finally:
            context.close()
            browser.close()


def run_cancel(target_date=None) -> None:
    today = datetime.now(PARIS_TZ).date()
    target = target_date or today
    target_str = target.isoformat()

    with sync_playwright() as p:
        browser, context = get_browser_context(p, headless=True)
        page = context.new_page()
        try:
            page.goto(APP_URL)
            page.wait_for_load_state("load")

            if ensure_authenticated(page, context):
                notify("Réauthentification réussie ✅", "Session renouvelée automatiquement", silent=_is_silent_day())

            cancel(page, target)
            _update_status(target_str, "cancelled")
            notify("Annulation réussie ✅", f"Réservation annulée pour le {target_str}")

        except Exception as e:
            notify("Erreur annulation ❌", f"{target_str} — {e}")
            raise
        finally:
            context.close()
            browser.close()


def run_checkin() -> None:
    today = datetime.now(PARIS_TZ).date()
    today_str = today.isoformat()
    today_status = _load_bookings().get(today_str, "")
    is_ooo = today_status.startswith("out of office")

    skip = check_skip_commands()

    if SKIP in skip:
        silent = _is_silent_day()
        if is_ooo:
            notify("Action ignorée ⏭️", f"Annulation ignorée pour le {today_str} (skip)", silent=silent)
            print(f"[checkin] skip — annulation skipped for {today_str}")
        else:
            notify("Action ignorée ⏭️", f"Check-in ignoré pour le {today_str} (skip)", silent=silent)
            print(f"[checkin] skip — check-in skipped for {today_str}")
        return

    with sync_playwright() as p:
        browser, context = get_browser_context(p, headless=True)
        page = context.new_page()
        try:
            page.goto(APP_URL)
            page.wait_for_load_state("load")

            if ensure_authenticated(page, context):
                notify("Réauthentification réussie ✅", "Session renouvelée automatiquement", silent=_is_silent_day())

            if is_ooo:
                try:
                    cancel(page, today)
                    _update_status(today_str, "cancelled")
                    notify("Annulation réussie ✅", f"Réservation annulée pour le {today_str} ({today_status})", silent=_is_silent_day())
                except RuntimeError as e:
                    if "No booking found" in str(e):
                        print(f"[checkin] No booking to cancel for {today_str} ({today_status}) — nothing to do.")
                    else:
                        raise
            else:
                checkin(page)
                _update_status(today_str, "checked_in")
                notify("Check-in réussi ✅", f"Check-in effectué pour le {today_str}", silent=_is_silent_day())

        except Exception as e:
            notify("Erreur check-in/annulation ❌", f"{today_str} — {e}")
            raise
        finally:
            context.close()
            browser.close()


def run_sync() -> None:
    import holidays as holidays_lib

    today = datetime.now(PARIS_TZ).date()
    end = today + timedelta(days=89)

    fr_holidays = holidays_lib.France()
    ooo_cal = get_ooo_calendar_days(today, end)
    bookings = _load_bookings()

    OOO_STATUSES = ("out of office - remote", "out of office - holidays", "out of office - public holiday")

    changed = 0
    for i in range(90):
        d = today + timedelta(days=i)
        if d.weekday() >= 5:
            continue

        d_str = d.isoformat()
        current = bookings.get(d_str, "")

        cal_reason = ooo_cal.get(d)  # 'remote', 'holidays', or None
        is_bank_holiday = d in fr_holidays

        # Priority: holidays > public holiday > remote
        if cal_reason == "holidays":
            new_ooo = "out of office - holidays"
        elif is_bank_holiday:
            new_ooo = "out of office - public holiday"
        elif cal_reason == "remote":
            new_ooo = "out of office - remote"
        else:
            new_ooo = None

        if new_ooo:
            if current != new_ooo:
                bookings[d_str] = new_ooo
                changed += 1
        else:
            # Clear any stale OOO status (remote event removed, holiday period ended, etc.)
            if current in OOO_STATUSES:
                del bookings[d_str]
                changed += 1

    if changed:
        _save_bookings(bookings)
        notify("Calendrier synchronisé 📅", f"{changed} jour(s) mis à jour", silent=True)
    else:
        print("[sync] No changes detected.")


def run_calendar_reminder() -> None:
    today = datetime.now(PARIS_TZ).date()
    if not has_remote_events_next_week(today):
        notify("Alerte Calendrier ⚠️", "Events de télétravail non renseignés")


def run_auth() -> None:
    print("Opening browser for manual authentication...")
    with sync_playwright() as p:
        browser, context = get_browser_context(p, headless=False)
        page = context.new_page()
        page.goto(APP_URL)
        print("Log in and approve the 2FA on your phone, then press Enter here...")
        input()
        save_session(context)
        context.close()
        browser.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "book"

    if mode == "book":
        run_book()
    elif mode == "cancel":
        run_cancel()
    elif mode == "checkin":
        run_checkin()
    elif mode == "sync":
        run_sync()
    elif mode == "reminder":
        run_calendar_reminder()
    elif mode == "auth":
        run_auth()
    else:
        print(f"Unknown mode '{mode}'. Usage: python src/main.py [book|cancel|checkin|sync|reminder|auth]")
        sys.exit(1)
