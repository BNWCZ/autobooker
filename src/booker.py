import re
from datetime import date, datetime

import pytz
from playwright.sync_api import Page

APP_URL = "https://doorjames.app"
PARIS_TZ = pytz.timezone("Europe/Paris")

# SVG path that identifies the forward (next month) arrow in the MUI datepicker
_FORWARD_ARROW_PATH = "M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6-1.41-1.41z"


def book(page: Page, target_date: date) -> None:
    today = datetime.now(PARIS_TZ).date()
    months_to_advance = (target_date.year - today.year) * 12 + (target_date.month - today.month)

    # 1. Navigate to bookings overview
    page.goto(f"{APP_URL}/bookingsOverview")
    page.wait_for_load_state("networkidle")

    # 2. Switch to "Past Bookings" tab
    page.locator(".content-switcher-item").filter(has_text=re.compile("^Past Bookings$")).click()
    page.wait_for_load_state("networkidle")

    # 3. Find the first eligible past booking (checkOutForgotten or cancelled)
    eligible = _find_eligible_booking(page)
    if eligible is None:
        raise RuntimeError("No eligible past booking found (status: checkOutForgotten or cancelled)")

    # 4. Open action sheet via ellipsis icon
    eligible.locator(".booking-item-icon-labels").click()

    # 5. Click "Book" in the action sheet
    page.locator(".action-sheet-option").filter(has_text=re.compile("^Book$")).click()
    page.wait_for_load_state("networkidle")

    # 6. Fill "From" date: target_date
    _fill_datepicker(page, label="From", target_date=target_date, months_to_advance=months_to_advance)

    # 7. Set "From" time: 09:00
    _fill_timepicker(page, label="From", hour="09", minute="00")

    # 8. Fill "To" date: same target_date
    _fill_datepicker(page, label="To", target_date=target_date, months_to_advance=months_to_advance)

    # 9. Set "To" time: 17:00
    _fill_timepicker(page, label="To", hour="17", minute="00")

    # 10. Save
    page.locator("button.button.primary.full-width.regular-height").filter(
        has=page.locator("span", has_text=re.compile("^Save$"))
    ).click()
    page.wait_for_load_state("networkidle")

    # 11. Confirm
    page.locator("button.button.primary.half-width.regular-height").filter(
        has=page.locator("span", has_text=re.compile("^Confirm$"))
    ).click()

    # 12. Verify success
    page.wait_for_selector(".modal-card.show .confirmation-wrapper", timeout=10_000)


def _find_eligible_booking(page: Page):
    items = page.locator(".booking-item")
    for i in range(items.count()):
        item = items.nth(i)
        status = item.locator(".booking-item-status")
        if status.count() == 0:
            continue
        cls = status.get_attribute("class") or ""
        if "status-checkOutForgotten" in cls or "status-cancelled" in cls:
            return item
    return None


def _fill_datepicker(page: Page, label: str, target_date: date, months_to_advance: int) -> None:
    wrapper = page.locator(".date-time-input-wrapper").filter(
        has=page.locator(".date-time-input-label", has_text=re.compile(f"^{label}$"))
    )
    wrapper.locator(".datepicker-wrapper").click()

    # Advance to the correct month
    forward_btn = page.locator(f'button:has(path[d="{_FORWARD_ARROW_PATH}"])')
    for _ in range(months_to_advance):
        forward_btn.click()
        page.wait_for_timeout(300)

    # Click the correct day (exact match to avoid e.g. clicking "1" inside "12")
    page.locator("button.MuiPickersDay-day:not(.MuiPickersDay-dayDisabled)").filter(
        has=page.locator("p.MuiTypography-body2", has_text=re.compile(f"^{target_date.day}$"))
    ).click()

    # Confirm date selection
    page.locator("span.MuiButton-label", has_text=re.compile("^Ok$")).click()


def _fill_timepicker(page: Page, label: str, hour: str, minute: str) -> None:
    wrapper = page.locator(".date-time-input-wrapper").filter(
        has=page.locator(".date-time-input-label", has_text=re.compile(f"^{label}$"))
    )
    # Click to open the time picker
    wrapper.locator(".timepicker-wrapper").click()

    # The rc-time-picker panels render globally — only the active picker's panels are visible
    panels = page.locator(".rc-time-picker-panel-select:visible")
    panels.nth(0).locator("li", has_text=re.compile(f"^{hour}$")).click()
    panels.nth(1).locator("li", has_text=re.compile(f"^{minute}$")).click()
