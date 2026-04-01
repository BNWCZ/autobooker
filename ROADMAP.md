# JoorDames — Roadmap

## Pending

### Discord skip commands
Allow the operator to send `skip checkin` or `skip delete` from Discord to override the next scheduled action, without CLI access.

**How it works:**
- Operator creates a Discord bot (Developer Portal) with Read Messages + Manage Messages permissions
- Bot token + command channel ID added to `.env`
- Before checkin/delete runs, script reads recent messages from the command channel via Discord REST API (no persistent bot process needed — fits the cron model)
- If a matching unprocessed skip command is found: skip the action, delete the command message, send a confirmation notification
- Needs new env vars: `DISCORD_BOT_TOKEN`, `DISCORD_COMMAND_CHANNEL_ID`
- Start session by creating the Discord bot, then implement step by step

---

### Re-book a day when BTT event is removed from calendar
When the `sync` script runs and detects that a previously set `out of office - BTT` status
no longer has a corresponding BTT event in Google Calendar, it clears the status from the CSV.
However, the booking script only runs once per day 41 days ahead, so the cleared day won't be
automatically rebooked.

Proposed solution: an ad-hoc booking mode that accepts a `--date` argument, callable manually
or triggered by the sync script when it detects a cleared BTT status.
