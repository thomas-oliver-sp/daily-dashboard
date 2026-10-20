"""Close-date pressure and the services-book status cadence.

The clock is the report date. A close on that date is already due. Coming up
means the following 14 days. Status cadence applies only to the closing
services book, using services value:

- 0 through 50,000: a status at least every 30 days
- above 50,000 through 100,000: every 14 days
- above 100,000: every 7 days

A blank status date is overdue. A negative value is outside the rule.
"""

from __future__ import annotations

from datetime import date, timedelta

SOON_DAYS = 14
WEEKLY_DAYS = 7
FORTNIGHT_DAYS = 14
MONTHLY_DAYS = 30

MONTHLY_MAX = 50_000
FORTNIGHT_MAX = 100_000


def close_timing(close: date | None, as_of: date, soon_days: int = SOON_DAYS) -> str:
    if close is None:
        return ""
    if close <= as_of:
        return "due"
    if close <= as_of + timedelta(days=soon_days):
        return "soon"
    return "later"


def status_band(value: float | None) -> str:
    if value is None or value < 0:
        return ""
    if value > FORTNIGHT_MAX:
        return "weekly"
    if value > MONTHLY_MAX:
        return "fortnightly"
    return "monthly"


def status_limit(band: str) -> int | None:
    return {
        "weekly": WEEKLY_DAYS,
        "fortnightly": FORTNIGHT_DAYS,
        "monthly": MONTHLY_DAYS,
    }.get(band)


def status_age(status: date | None, as_of: date) -> int | None:
    if status is None:
        return None
    return (as_of - status).days


def status_fresh(value: float | None, status: date | None, as_of: date) -> bool | None:
    limit = status_limit(status_band(value))
    if limit is None:
        return None
    age = status_age(status, as_of)
    if age is None:
        return False
    return age <= limit
