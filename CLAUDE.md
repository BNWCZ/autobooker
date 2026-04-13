# JoorDames — Project Instructions

> Context document for Claude sessions working on this project.
> Read this before doing anything else.

---

## What this is

A Python automation script that manages desk reservations on [doorjames.app](https://doorjames.app) (CGI's desk booking PWA). It runs on a schedule, checks Google Calendar to determine office presence, books/cancels/checks in accordingly, and sends Discord notifications for every significant event.

This is a personal productivity tool, unrelated to the homelab infrastructure in `/opt/docker`.

---

## Starting point

The project is based on an existing working implementation. Before writing any new code, read the existing repo in its entirety and understand what it already does.

The operator will provide the GitHub URL at the start of the session — clone it here into `~/JoorDames/` and use it as the base.

---

## Tech stack

| Component | Choice | Reason |
|---|---|---|
| Automation | Python + Playwright | Better than Selenium for modern PWAs |
| Base image | `mcr.microsoft.com/playwright/python` | Chrome bundled, maintained |
| Scheduling | Host cron → `docker compose run --rm joordames` | Simple, no in-container scheduler |
| Notifications | Discord webhook | Free, no bot setup, one HTTP call |
| Calendar | Google Calendar API (service account) | Fully automatable, no OAuth dance |
| Secrets | `.env` file (never committed) | Credentials stored locally |

---

## Authentication

- **doorjames.app login**: username + password stored in `.env`
- **2FA**: Microsoft Authenticator (operator's company phone) — cannot be automated
- **Session management**: Playwright `storageState` — authenticate once manually (script pauses, operator approves 2FA on phone), session saved to a local file, reused on all subsequent runs until expiry
- When session expires, the script must detect this and prompt for re-authentication (not fail silently)

---

## Behaviour

The script should:

1. Check Google Calendar for the current day (and upcoming days as needed)
2. If operator is in the office → book the desk, check in at the right time
3. If operator is not in the office → cancel any existing reservation
4. Send Discord notifications for: successful booking, successful check-in, successful cancellation, session expiry warning, any error

Specific trigger events (which calendar event name to watch, how far in advance to book, check-in window) should be confirmed with the operator before implementing.

---

## Project structure (target)

```
~/JoorDames/
├── CLAUDE.md               # This file
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── .env                    # Never committed
├── session/                # Playwright storageState (never committed)
│   └── state.json
└── src/
    ├── main.py
    ├── booker.py            # doorjames.app automation
    ├── calendar.py          # Google Calendar logic
    └── notifier.py          # Discord webhook
```

---

## What to do at session start

1. Read this file
2. Ask the operator for the existing GitHub repo URL
3. Read all existing code before proposing any changes
4. Confirm with the operator what changes they want to make
5. Then plan and implement

---

## Constraints

- Never commit `.env` or `session/` — add both to `.gitignore`
- Always confirm behaviour changes with the operator before implementing
- Keep it simple — this is a single-user personal tool, not a product

---

## Operations handled by Claude Code (not the operator)

- Creating, editing, or deleting files and directories
- Building Docker images (`docker compose build`)
- Running Docker containers (`docker compose run`)
- Git operations (add, commit, push)
- Any other shell/file system task — the operator should not need to run commands themselves

---

## Error log — learn from each mistake, never repeat it

Each error encountered during this project is logged here. Claude must not make the same mistake twice.

| # | Error | Rule |
|---|-------|------|
| 1 | `Write` tool called without reading the file first → `File has not been read yet` | Always `Read` before `Write` on existing files |
| 2 | Used `glob` pattern in a `Write` file path | `Write` requires an exact absolute path — no wildcards, no patterns |
| 3 | Refactored `run()` to accept `None` defaults but left `__main__` passing hardcoded values — dynamic logic silently ignored | When adding dynamic defaults to a function, update the call site too |
| 4 | Ran `docker compose run` in background, saw "Created" and assumed stuck, killed it — container was just slow to start (Playwright/Chrome init ~30s) | Always run `docker compose run` in foreground with sufficient timeout; never background it |
