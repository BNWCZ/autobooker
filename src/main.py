import csv
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytz
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

from auth import get_browser_context, is_session_expired, save_session
from booker import book, cancel, checkin
from calendar_client import has_btt_event, has_btt_events_next_week
from notifier import notify

PARIS_TZ = pytz.timezone("Europe/Paris")
APP_URL = os.getenv("APP_URL", "https://doorjames.app")
BOOKINGS_PATH = Path(os.getenv("BOOKINGS_PATH", "bookings.csv"))

DAYS_AHEAD = 41


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
    if existing in ("booked", "checked_in"):
        print(f"[book] {target_str} already has status '{existing}' — skipping.")
        return

    with sync_playwright() as p:
        browser, context = get_browser_context(p, headless=True)
        page = context.new_page()
        try:
            page.goto(APP_URL)
            page.wait_for_load_state("load")

            if is_session_expired(page):
                notify("Session expirée", "Lancez `python src/main.py auth` pour renouveler la session.")
                return

            book(page, target)
            _update_status(target_str, "booked")
            notify("Réservation réussie ✅", f"Bureau réservé pour le {target_str} (09:00–17:00)")

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

            if is_session_expired(page):
                notify("Session expirée", "Lancez `python src/main.py auth` pour renouveler la session.")
                return

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

    with sync_playwright() as p:
        browser, context = get_browser_context(p, headless=True)
        page = context.new_page()
        try:
            page.goto(APP_URL)
            page.wait_for_load_state("load")

            if is_session_expired(page):
                notify("Session expirée", "Lancez `python src/main.py auth` pour renouveler la session.")
                return

            if has_btt_event(today):
                cancel(page, today)
                _update_status(today_str, "cancelled")
                notify("Annulation réussie ✅", f"Réservation annulée pour le {today_str} (BTT)")
            else:
                checkin(page)
                _update_status(today_str, "checked_in")
                notify("Check-in réussi ✅", f"Check-in effectué pour le {today_str}")

        except Exception as e:
            notify("Erreur check-in/annulation ❌", f"{today_str} — {e}")
            raise
        finally:
            context.close()
            browser.close()


def run_calendar_reminder() -> None:
    today = datetime.now(PARIS_TZ).date()
    if not has_btt_events_next_week(today):
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
    elif mode == "reminder":
        run_calendar_reminder()
    elif mode == "auth":
        run_auth()
    else:
        print(f"Unknown mode '{mode}'. Usage: python src/main.py [book|cancel|checkin|reminder|auth]")
        sys.exit(1)
