import os

import requests

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")


def notify(event: str, detail: str = "") -> None:
    msg = f"**[JoorDames]** {event}"
    if detail:
        msg += f"\n{detail}"

    if not WEBHOOK_URL:
        print(f"[notifier] {msg}")
        return

    try:
        requests.post(WEBHOOK_URL, json={"content": msg}, timeout=10)
    except Exception as e:
        print(f"[notifier] Discord send failed: {e}")
