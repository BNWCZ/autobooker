import os
from pathlib import Path

from playwright.sync_api import Browser, BrowserContext, Playwright

STATE_PATH = Path(os.getenv("SESSION_STATE_PATH", "session/state.json"))
APP_DOMAIN = "spa.doorjames.app"
APP_URL = os.getenv("APP_URL", "https://spa.doorjames.app")


def get_browser_context(playwright: Playwright, headless: bool = True) -> tuple[Browser, BrowserContext]:
    browser = playwright.chromium.launch(
        headless=headless,
        args=["--no-sandbox", "--disable-dev-shm-usage"],
    )
    context_kwargs = {
        "timezone_id": "Europe/Paris",
        "locale": "fr-FR",
    }
    if STATE_PATH.exists():
        context = browser.new_context(storage_state=str(STATE_PATH), **context_kwargs)
    else:
        context = browser.new_context(**context_kwargs)
    return browser, context


def is_session_expired(page) -> bool:
    """Returns True if the current page is not on the app domain (i.e. redirected to auth)."""
    return APP_DOMAIN not in page.url


def save_session(context: BrowserContext) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    context.storage_state(path=str(STATE_PATH))
    print(f"Session saved to {STATE_PATH}")


def ensure_authenticated(page, context: BrowserContext) -> bool:
    """
    Returns False if the session is still valid (no-op).
    Returns True after a successful headless re-authentication.
    Raises RuntimeError if re-authentication fails.
    """
    if not is_session_expired(page):
        return False

    username = os.getenv("DOORJAMES_USERNAME", "")
    password = os.getenv("DOORJAMES_PASSWORD", "")
    if not username or not password:
        raise RuntimeError("DOORJAMES_USERNAME or DOORJAMES_PASSWORD not set in .env")

    # Step 1 — email
    page.wait_for_selector("input[name='loginfmt']", timeout=10_000)
    page.fill("input[name='loginfmt']", username)
    page.click("#idSIButton9")

    # Step 2 — password
    page.wait_for_selector("input[name='passwd']", timeout=10_000)
    page.fill("input[name='passwd']", password)
    page.click("#idSIButton9")

    # Wait for post-login navigation to settle
    page.wait_for_load_state("networkidle", timeout=30_000)

    # Step 3 — "Stay signed in?" interstitial (click No)
    if APP_DOMAIN not in page.url:
        try:
            page.wait_for_selector("#idBtn_Back", timeout=5_000)
            page.click("#idBtn_Back")
            page.wait_for_load_state("networkidle", timeout=30_000)
        except Exception:
            pass

    if APP_DOMAIN not in page.url:
        raise RuntimeError(
            "MFA required or authentication failed — "
            "run `python src/main.py auth` to refresh manually"
        )

    save_session(context)
    return True
