import os

import requests

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")


_SUPPRESS_NOTIFICATIONS = 1 << 12


def notify(event: str, detail: str = "", silent: bool = False) -> None:
    msg = f"**[JoorDames]** {event}"
    if detail:
        msg += f"\n{detail}"

    if not WEBHOOK_URL:
        print(f"[notifier] {msg}")
        return

    payload = {"content": msg}
    if silent:
        payload["flags"] = _SUPPRESS_NOTIFICATIONS

    try:
        requests.post(WEBHOOK_URL, json=payload, timeout=10)
    except Exception as e:
        print(f"[notifier] Discord send failed: {e}")
