import os
from pathlib import Path

from playwright.sync_api import Browser, BrowserContext, Playwright

STATE_PATH = Path(os.getenv("SESSION_STATE_PATH", "session/state.json"))
APP_DOMAIN = "doorjames.app"


def get_browser_context(playwright: Playwright, headless: bool = True) -> tuple[Browser, BrowserContext]:
    browser = playwright.chromium.launch(
        headless=headless,
        args=["--no-sandbox", "--disable-dev-shm-usage"],
    )
    if STATE_PATH.exists():
        context = browser.new_context(storage_state=str(STATE_PATH))
    else:
        context = browser.new_context()
    return browser, context


def is_session_expired(page) -> bool:
    """Returns True if the current page is not on the app domain (i.e. redirected to auth)."""
    return APP_DOMAIN not in page.url


def save_session(context: BrowserContext) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    context.storage_state(path=str(STATE_PATH))
    print(f"Session saved to {STATE_PATH}")
