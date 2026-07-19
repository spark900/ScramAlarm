"""Flexible time-string parsing for alarm-tui.

Supported forms:
    +30m / +2h / +90s / +1h30m   -> relative offset from now
    07:30 / 7:30 / 23:05:00      -> next occurrence of that clock time
    2026-07-20 07:30             -> absolute date + time
    2026-07-20T07:30:00          -> absolute ISO-style date + time
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Optional

_RELATIVE_RE = re.compile(
    r"^\+(?:(?P<hours>\d+)h)?(?:(?P<minutes>\d+)m)?(?:(?P<seconds>\d+)s)?$"
)
_CLOCK_RE = re.compile(r"^(?P<hour>\d{1,2}):(?P<minute>\d{2})(?::(?P<second>\d{2}))?$")
_ABSOLUTE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
)


class TimeParseError(ValueError):
    """Raised when a user-supplied time string cannot be parsed."""


def parse_alarm_time(raw: str, *, now: Optional[datetime] = None) -> datetime:
    """Parse ``raw`` into a concrete future :class:`datetime`.

    Raises :class:`TimeParseError` with a human-readable message on any
    invalid input, so callers (CLI or TUI) can surface it directly.
    """
    raw = raw.strip()
    if not raw:
        raise TimeParseError("Empty time string.")
    now = now or datetime.now()

    if raw.startswith("+"):
        match = _RELATIVE_RE.match(raw)
        if not match or not any(match.groupdict().values()):
            raise TimeParseError(
                f"Invalid relative time '{raw}'. Expected forms like +30m, +1h, +1h30m."
            )
        hours = int(match.group("hours") or 0)
        minutes = int(match.group("minutes") or 0)
        seconds = int(match.group("seconds") or 0)
        delta = timedelta(hours=hours, minutes=minutes, seconds=seconds)
        if delta.total_seconds() <= 0:
            raise TimeParseError("Relative offset must be greater than zero.")
        return now + delta

    clock_match = _CLOCK_RE.match(raw)
    if clock_match:
        hour = int(clock_match.group("hour"))
        minute = int(clock_match.group("minute"))
        second = int(clock_match.group("second") or 0)
        if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
            raise TimeParseError(f"Invalid clock time '{raw}'.")
        candidate = now.replace(hour=hour, minute=minute, second=second, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate

    for fmt in _ABSOLUTE_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue

    raise TimeParseError(
        f"Could not parse '{raw}'. Use forms like +30m, 07:30, or 2026-07-20 07:30."
    )
