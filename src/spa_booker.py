"""
JoorDames SPA — booking / cancel / check-in primitives.

Each function takes an already-authenticated Playwright ``Page`` and returns a
details dict on success so ``main.py`` can feed rich Discord notifications.
Browser/context lifecycle is owned by the caller.
"""

import os
from datetime import date, datetime
from typing import Optional

import pytz
from playwright.sync_api import Page

PARIS_TZ = pytz.timezone("Europe/Paris")

BOOKING_AREA = os.getenv("BOOKING_AREA", "D2")
BOOKING_DESK = os.getenv("BOOKING_DESK", "D2 C 11-Q")

_START_HOUR, _START_MINUTE = 9, 0
_END_HOUR, _END_MINUTE = 17, 0

STATUS_CLASSES = [
    "confirmed",
    "checkInOpen",
    "checkedIn",
    "cancelled",
    "declined",
    "checkedOut",
    "expired",
    "checkOutForgotten",
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def book(page: Page, target_date: date) -> dict:
    today = datetime.now(PARIS_TZ).date()
    month_offset = (target_date.year - today.year) * 12 + (target_date.month - today.month)

    fab = page.locator("button.mdc-fab.mat-mdc-fab").first
    fab.wait_for(state="visible", timeout=8000)
    fab.click()
    page.wait_for_timeout(600)

    resa_btn = page.locator(".fab-action[aria-label='Réservation']")
    resa_btn.wait_for(state="visible", timeout=5000)
    resa_btn.click()

    office = page.locator("djs-office-banner").first
    office.wait_for(state="visible", timeout=15_000)
    office.click()
    page.wait_for_timeout(600)

    bureau = page.locator(".widget-banner.padded").first
    bureau.wait_for(state="visible", timeout=5000)
    bureau.click()
    page.wait_for_timeout(600)

    continuer = page.locator(".fab-button-context", has_text="Continuer")
    continuer.wait_for(state="visible", timeout=5000)
    continuer.click()

    page.locator(".mat-calendar-body-cell-content").first.wait_for(
        state="visible", timeout=15_000,
    )

    _navigate_to_month(page, month_offset)

    day_cell = page.locator(
        ".mat-calendar-body-cell-content",
        has_text=str(target_date.day),
    ).first
    day_cell.wait_for(state="visible", timeout=5000)
    day_cell.click()
    page.wait_for_timeout(400)

    _set_time_field(page, 0, _START_HOUR, _START_MINUTE)
    _set_time_field(page, 1, _END_HOUR, _END_MINUTE)

    carte = page.locator(".fab-button-context", has_text="Afficher la carte")
    carte.wait_for(state="visible", timeout=5000)
    carte.click(force=True)

    area_btn = page.locator("djs-area-selector button").first
    area_btn.wait_for(state="visible", timeout=15_000)
    area_btn.click()
    page.wait_for_timeout(800)

    desk_widget = page.locator(
        ".mat-ripple.widget-item",
        has=page.locator(".widget-label", has_text=BOOKING_AREA),
    ).first
    desk_widget.wait_for(state="visible", timeout=5000)
    desk_widget.click()
    page.wait_for_timeout(600)

    drawer_btn = page.locator("button.drawer-toggle-btn")
    drawer_btn.wait_for(state="visible", timeout=5000)
    drawer_btn.click()
    page.wait_for_timeout(600)

    search = page.locator("input[placeholder*='Rechercher']")
    search.wait_for(state="visible", timeout=5000)
    search.fill(BOOKING_DESK)
    page.wait_for_timeout(800)

    zone_header = page.locator("djs-list-item.zone-header .djs-list-item")
    zone_header.wait_for(state="visible", timeout=5000)
    zone_header.click()
    page.wait_for_timeout(600)

    desk_item = page.locator(
        "djs-teak-entity-item",
        has=page.locator("h2.truncate-text", has_text=BOOKING_DESK),
    ).first
    desk_item.wait_for(state="visible", timeout=5000)
    page.wait_for_timeout(300)
    desk_item.click()
    page.wait_for_timeout(600)

    selectionner = page.locator(
        ".mat-mdc-nav-list .mdc-list-item__content", has_text="Sélectionner"
    ).first
    selectionner.wait_for(state="visible", timeout=5000)
    selectionner.click()
    page.wait_for_timeout(600)

    confirmer = page.locator(".fab-button-context", has_text="Confirmer")
    confirmer.wait_for(state="visible", timeout=5000)
    confirmer.click()

    if not _verify_booking(page):
        raise RuntimeError("Booking verification failed")

    return {
        "desk": BOOKING_DESK,
        "area": BOOKING_AREA,
        "date": target_date.strftime("%d/%m/%Y"),
        "start": f"{_START_HOUR:02d}:{_START_MINUTE:02d}",
        "end": f"{_END_HOUR:02d}:{_END_MINUTE:02d}",
    }


def cancel(page: Page, target_date: Optional[date] = None) -> dict:
    """Cancel today's active booking for BOOKING_DESK.

    The SPA homepage exposes today's booking card; ``target_date`` is accepted
    for API compatibility with the old booker but not used for selection.
    """
    today = (target_date or datetime.now(PARIS_TZ).date()).strftime("%d/%m/%Y")

    page.wait_for_selector("button.mdc-fab", timeout=30_000)
    page.wait_for_timeout(2000)

    card = page.locator(
        "djs-dashboard-item",
        has=page.locator("h2", has_text=BOOKING_DESK),
    ).filter(
        has_not=page.locator(
            ".djs-status-tag.cancelled, "
            ".djs-status-tag.expired, "
            ".djs-status-tag.checkedOut"
        )
    ).first
    try:
        card.wait_for(state="visible", timeout=15_000)
    except Exception:
        raise RuntimeError("No booking found to cancel")

    start, end = _card_time_range(card)

    tag = card.locator(".djs-status-tag").first
    tag_cls = (tag.get_attribute("class") or "") if tag.count() > 0 else ""
    if "checkedIn" in tag_cls.split():
        raise RuntimeError(
            "Cannot cancel a checked-in booking — only check-out is available "
            "once the user has checked in."
        )

    card.click()
    page.wait_for_timeout(800)

    annuler = page.locator(
        ".mdc-list-item__primary-text", has_text="Annuler la réservation"
    ).first
    annuler.wait_for(state="visible", timeout=5000)
    annuler.click()
    page.wait_for_timeout(800)

    confirm_btn = page.locator(
        "mat-dialog-actions button.confirmation-button-danger"
    ).first
    confirm_btn.wait_for(state="visible", timeout=5000)
    confirm_btn.click()
    page.wait_for_timeout(1500)

    cancelled_chip = page.locator(
        "djs-dashboard-item",
        has=page.locator("h2", has_text=BOOKING_DESK),
    ).locator(".djs-status-tag.cancelled").first
    try:
        cancelled_chip.wait_for(state="visible", timeout=5000)
    except Exception:
        raise RuntimeError("Cancellation could not be verified")

    return {
        "desk": BOOKING_DESK,
        "area": BOOKING_AREA,
        "date": today,
        "start": start,
        "end": end,
    }


def checkin(page: Page) -> dict:
    """Check in today's active booking for BOOKING_DESK."""
    today = datetime.now(PARIS_TZ).date().strftime("%d/%m/%Y")

    page.wait_for_selector("button.mdc-fab", timeout=30_000)
    page.wait_for_timeout(2000)

    card = page.locator(
        "djs-dashboard-item",
        has=page.locator("h2", has_text=BOOKING_DESK),
    ).filter(
        has_not=page.locator(
            ".djs-status-tag.cancelled, "
            ".djs-status-tag.expired, "
            ".djs-status-tag.checkedOut"
        )
    ).first
    try:
        card.wait_for(state="visible", timeout=15_000)
    except Exception:
        raise RuntimeError("No booking found to check in")

    start, end = _card_time_range(card)
    state = _card_status(card)
    if state == "checkedIn":
        raise RuntimeError("Booking is already checked in — nothing to do.")
    if state != "checkInOpen":
        raise RuntimeError(
            f"Check-in not available — card state is '{state or 'unknown'}', "
            "expected 'checkInOpen'. Check-in opens 30 minutes before the "
            "booking start time."
        )

    card.click()
    page.wait_for_timeout(800)

    checkin_item = page.locator(
        ".mdc-list-item__primary-text", has_text="Check-in"
    ).first
    checkin_item.wait_for(state="visible", timeout=5000)
    checkin_item.click()
    page.wait_for_timeout(1500)

    checked_chip = page.locator(
        "djs-dashboard-item",
        has=page.locator("h2", has_text=BOOKING_DESK),
    ).locator(".djs-status-tag.checkedIn").first
    try:
        checked_chip.wait_for(state="visible", timeout=8000)
    except Exception:
        raise RuntimeError("Check-in could not be verified")

    return {
        "desk": BOOKING_DESK,
        "area": BOOKING_AREA,
        "date": today,
        "start": start,
        "end": end,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _navigate_to_month(page: Page, offset: int) -> None:
    next_btn = page.locator("button.mat-calendar-next-button")
    for _ in range(offset):
        next_btn.click()
        page.wait_for_timeout(400)


def _set_time_field(page: Page, field_index: int, hour: int, minute: int) -> None:
    infix = page.locator(".mat-mdc-form-field-infix").nth(field_index)
    infix.locator("input").click()
    page.wait_for_timeout(400)

    mode_toggle = page.locator(".picker-actions .mode-toggle button")
    mode_toggle.wait_for(state="visible", timeout=3000)
    mode_toggle.click()
    page.wait_for_timeout(300)

    def _set_field(selector: str, value: str):
        field = page.locator(selector)
        field.wait_for(state="visible", timeout=3000)
        field.evaluate(
            """(el, v) => {
                const setter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value'
                ).set;
                setter.call(el, v);
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
                el.blur();
            }""",
            value,
        )
        page.wait_for_timeout(200)

    _set_field("input.time-input-box[aria-label='Heure']", f"{hour:02d}")
    _set_field("input.time-input-box[aria-label='Minute']", f"{minute:02d}")

    ok_btn = page.locator(".picker-actions button", has_text="OK")
    if ok_btn.count() > 0 and ok_btn.first.is_visible():
        ok_btn.first.click()
        page.wait_for_timeout(300)

    backdrop = page.locator(".cdk-overlay-backdrop.cdk-overlay-backdrop-showing")
    if backdrop.count() > 0:
        try:
            backdrop.first.wait_for(state="detached", timeout=3000)
        except Exception:
            pass


def _verify_booking(page: Page) -> bool:
    toast = page.locator(
        "mat-snack-bar-container", has_text="Réservation confirmée"
    )
    try:
        toast.wait_for(state="visible", timeout=5000)
        return True
    except Exception:
        pass

    try:
        app_url = os.getenv("APP_URL", "https://spa.doorjames.app")
        page.goto(f"{app_url}/agenda")
        match = page.locator(
            "djs-dashboard-item",
            has=page.locator("h2", has_text=BOOKING_DESK),
        )
        match.first.wait_for(state="visible", timeout=15_000)
        return True
    except Exception:
        return False


def _card_time_range(card_locator) -> tuple[str, str]:
    span = card_locator.locator(".time-range").first
    if span.count() == 0:
        return "", ""
    txt = (span.inner_text() or "").strip()
    parts = [p.strip() for p in txt.split("-")]
    if len(parts) == 2 and all(":" in p for p in parts):
        return parts[0], parts[1]
    return "", ""


def _card_status(card_locator) -> str:
    tag = card_locator.locator(".djs-status-tag").first
    if tag.count() == 0:
        return ""
    cls = tag.get_attribute("class") or ""
    for s in STATUS_CLASSES:
        if s in cls.split():
            return s
    return ""
