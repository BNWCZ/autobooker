import os
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Browser, BrowserContext, Playwright, TimeoutError as PlaywrightTimeout

from notifier import notify

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


def _is_on_app(page) -> bool:
    """True when the page is on the app domain AND past the login screen."""
    return APP_DOMAIN in page.url and "/login" not in page.url


DEBUG_DIR = Path("debug_out")


def _dump_debug(page, label: str) -> None:
    DEBUG_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = f"{ts}_{label}"
    try:
        page.screenshot(path=str(DEBUG_DIR / f"{prefix}.png"), full_page=True, timeout=10_000)
    except Exception as exc:
        print(f"[debug] screenshot failed for {prefix}: {exc}")
    try:
        with open(DEBUG_DIR / f"{prefix}.html", "w") as f:
            f.write(page.content())
    except Exception as exc:
        print(f"[debug] html dump failed for {prefix}: {exc}")
    print(f"[debug] saved {prefix}  url={page.url}")


def _wait_for_page_ready(page, timeout: int = 30_000) -> None:
    """Wait until the SPA dashboard or a login form is visible."""
    selector = "button.mdc-fab, input[name='email'], input[name='loginfmt'], #idDiv_SAOTCAS_Title, #idRichContext_DisplaySign"
    try:
        page.wait_for_selector(selector, timeout=timeout)
    except PlaywrightTimeout:
        _dump_debug(page, "wait_for_page_ready_retry")
        print("[auth] page not ready, reloading and retrying once...")
        page.reload(wait_until="load")
        try:
            page.wait_for_selector(selector, timeout=timeout)
        except PlaywrightTimeout:
            _dump_debug(page, "wait_for_page_ready_failed")
            raise


def is_session_expired(page) -> bool:
    _wait_for_page_ready(page)
    if _is_on_app(page):
        return False
    return True


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
    ms_email = os.getenv("MICROSOFT_EMAIL", username)
    if not username or not password:
        raise RuntimeError(
            "Session expirée — DOORJAMES_USERNAME ou DOORJAMES_PASSWORD "
            "non configuré dans .env"
        )

    # Step 1 — Door James native login page: fill email, click Continue
    dj_email = page.locator("input[name='email']")
    if dj_email.count() > 0:
        dj_email.fill(username)
        page.wait_for_timeout(500)
        page.locator("button[type='submit']").click()
        page.wait_for_selector(
            "#tilesHolder, input[name='loginfmt'], input#i0118, button.mdc-fab",
            timeout=30_000,
        )
        page.wait_for_timeout(2000)

    # Step 2 — Microsoft: account picker OR email input
    if not _is_on_app(page):
        tile = page.locator("#tilesHolder > div").first
        ms_loginfmt = page.locator("input[name='loginfmt']")

        if tile.count() > 0:
            tile.click()
            page.wait_for_selector(
                "input#i0118, button.mdc-fab, #idBtn_Back",
                timeout=30_000,
            )
            page.wait_for_timeout(2000)
        elif ms_loginfmt.is_visible():
            ms_loginfmt.fill(ms_email)
            page.wait_for_timeout(300)
            page.click("#idSIButton9")
            page.wait_for_selector(
                "input#i0118, button.mdc-fab, #idBtn_Back",
                timeout=30_000,
            )
            page.wait_for_timeout(2000)

    # Step 3 — Microsoft password page (may be skipped if MS session is valid)
    if not _is_on_app(page):
        try:
            page.wait_for_selector(
                "input[name='loginfmt']", state="hidden", timeout=10_000
            )
        except Exception:
            pass
        page.wait_for_timeout(1000)
        page.fill("input#i0118", password)
        page.wait_for_timeout(500)
        page.click("#idSIButton9")
        page.wait_for_selector(
            "button.mdc-fab, #idBtn_Back, #idDiv_SAOTCAS_Title, #idRichContext_DisplaySign",
            timeout=30_000,
        )
        page.wait_for_timeout(2000)

    # Step 3b — Microsoft MFA approval (Authenticator push or number matching)
    if not _is_on_app(page):
        mfa_prompt = page.locator("#idDiv_SAOTCAS_Title, #idRichContext_DisplaySign")
        if mfa_prompt.count() > 0:
            number_el = page.locator("#idRichContext_DisplaySign")
            if number_el.count() > 0:
                code = number_el.inner_text().strip()
                notify("MFA requise 🔐", f"Approuvez la connexion sur votre téléphone (code : {code})")
            else:
                notify("MFA requise 🔐", "Approuvez la notification Microsoft Authenticator sur votre téléphone")
            _dump_debug(page, "mfa_waiting")
            page.wait_for_selector(
                "button.mdc-fab, #idBtn_Back", timeout=120_000,
            )
            page.wait_for_timeout(2000)

    # Step 4 — "Stay signed in?" interstitial (click No)
    if not _is_on_app(page):
        stay_btn = page.locator("#idBtn_Back")
        if stay_btn.count() > 0:
            stay_btn.click()
            page.wait_for_selector("button.mdc-fab", timeout=30_000)
            page.wait_for_timeout(2000)

    if not _is_on_app(page):
        raise RuntimeError(
            "Session expirée — réauthentification échouée "
            f"(MFA ou erreur de mot de passe). URL: {page.url}\n"
            f"Connectez-vous manuellement : {APP_URL}"
        )

    save_session(context)
    return True
