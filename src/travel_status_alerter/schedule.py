from datetime import datetime
from zoneinfo import ZoneInfo

UK_TZ = ZoneInfo("Europe/London")
RUN_HOUR = 7


def should_run(now: datetime) -> bool:
    """Return True if `now` falls within the 07:00 hour in UK local time.

    GitHub Actions cron is UTC-only, so the workflow fires at both 06:00 and 07:00 UTC and
    this guard lets exactly one of those through in both GMT and BST.
    """
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return now.astimezone(UK_TZ).hour == RUN_HOUR
