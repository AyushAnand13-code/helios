"""Seasonality calendar — known seasonal events whose moves are expected, not anomalies.

A move that lands in one of these windows is the kind of thing the eval's
`seasonality_decoy` bucket models: a large, real, store-wide swing that is NOT an
actionable root cause. The autonomous run consults this so it does not page the team on
Black Friday or the post-holiday January trough.

The dates below cover the GA4 sample window (2020-11 .. 2021-01). Recurring (month/day)
rules for other years are a future extension; for now membership is by explicit range.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class SeasonalEvent:
    name: str
    start: date
    end: date

    def covers(self, d: date) -> bool:
        return self.start <= d <= self.end


def _d(s: str) -> date:
    return date.fromisoformat(s)


# Mirrors the events behind eval/scenarios seasonality_decoy (S033–S038).
DEFAULT_EVENTS = [
    SeasonalEvent("Black Friday", _d("2020-11-26"), _d("2020-11-29")),
    SeasonalEvent("Cyber Monday", _d("2020-11-30"), _d("2020-12-01")),
    SeasonalEvent("Christmas peak", _d("2020-12-20"), _d("2020-12-26")),
    SeasonalEvent("New Year", _d("2020-12-31"), _d("2021-01-02")),
    SeasonalEvent("Post-holiday January trough", _d("2021-01-02"), _d("2021-01-15")),
]


class SeasonalityCalendar:
    def __init__(self, events: list[SeasonalEvent] | None = None):
        self.events = events if events is not None else list(DEFAULT_EVENTS)

    def event_on(self, d: date | str) -> SeasonalEvent | None:
        """The seasonal event covering a given day, or None."""
        if isinstance(d, str):
            d = date.fromisoformat(d)
        for ev in self.events:
            if ev.covers(d):
                return ev
        return None

    def event_for_week(self, week_start: date | str) -> SeasonalEvent | None:
        """The seasonal event overlapping the 7-day week beginning `week_start`
        (the diagnosis compares Monday-anchored weeks)."""
        if isinstance(week_start, str):
            week_start = date.fromisoformat(week_start)
        week_end = week_start + timedelta(days=6)
        for ev in self.events:
            if ev.start <= week_end and week_start <= ev.end:   # ranges overlap
                return ev
        return None


DEFAULT_CALENDAR = SeasonalityCalendar()
