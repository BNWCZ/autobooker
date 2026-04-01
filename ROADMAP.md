# JoorDames — Roadmap

## Pending

### Re-book a day when BTT event is removed from calendar
When the `sync` script runs and detects that a previously set `out of office - BTT` status
no longer has a corresponding BTT event in Google Calendar, it clears the status from the CSV.
However, the booking script only runs once per day 41 days ahead, so the cleared day won't be
automatically rebooked.

Proposed solution: an ad-hoc booking mode that accepts a `--date` argument, callable manually
or triggered by the sync script when it detects a cleared BTT status.
