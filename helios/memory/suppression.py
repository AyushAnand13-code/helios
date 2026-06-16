"""Suppression — should this finding page the team, or has it already / is it expected?

The autonomous run re-diagnoses every day; without this it would re-alert the same finding
and shout on every seasonal swing. `decide()` returns one status:

    NEW        — a genuine, fresh, actionable finding → alert + remember it.
    SEASONAL   — lands in a known seasonal window (Black Friday, January trough, …) → quiet.
    REFUTED    — the Critic refuted it (not a real growth problem) → quiet.
    IMMATERIAL — below the materiality floor / not worth paging → quiet.
    REPEAT     — already reported recently with the same fingerprint → quiet.

Only NEW findings are alerted and saved, so tomorrow's identical run stays quiet.
"""
from __future__ import annotations
from dataclasses import dataclass

from helios.critic import MATERIALITY_PTS
from .store import MemoryStore, DiagnosisRecord, finding_key
from .seasonality import SeasonalityCalendar, DEFAULT_CALENDAR

REPEAT_WINDOW_DAYS = 14


@dataclass
class SuppressionDecision:
    status: str            # NEW | SEASONAL | REFUTED | IMMATERIAL | REPEAT
    suppress: bool         # True => do not alert
    reason: str
    key: str


def decide(diagnosis, report, *, as_of: str, store: MemoryStore | None = None,
           calendar: SeasonalityCalendar | None = None,
           repeat_window_days: int = REPEAT_WINDOW_DAYS) -> SuppressionDecision:
    """Decide whether to alert on `diagnosis` (with its Critic `report`) on date `as_of`."""
    calendar = calendar or DEFAULT_CALENDAR
    seg = diagnosis.drivers[0]["segment"] if diagnosis.drivers else "(none)"
    key = finding_key(diagnosis.dominant, seg, diagnosis.delta)

    # 1. Seasonal window → expected, not actionable (mirrors the Critic-via-calendar defense).
    ev = calendar.event_for_week(diagnosis.w1)
    if ev is not None:
        return SuppressionDecision("SEASONAL", True,
                                   f"compare week overlaps {ev.name}; expected seasonal move", key)

    # 2. Critic refuted the finding → don't page it as a growth problem.
    if report.verdict == "REFUTE":
        why = report.failures[0].detail if report.failures else "failed an integrity check"
        return SuppressionDecision("REFUTED", True, f"Critic refuted: {why}", key)

    # 3. Below the materiality floor → noise, not a finding.
    if abs(diagnosis.delta) < MATERIALITY_PTS:
        return SuppressionDecision("IMMATERIAL", True,
                                   f"aggregate move {diagnosis.delta*100:+.3f}pt below "
                                   f"materiality floor", key)

    # 4. Already reported recently with the same fingerprint → don't repeat.
    if store is not None:
        prior = store.recall_prior(key, as_of=as_of, within_days=repeat_window_days)
        if prior:
            return SuppressionDecision("REPEAT", True,
                                       f"already reported {prior[0].as_of} (same finding)", key)

    # 5. Genuinely new and material → alert and remember.
    return SuppressionDecision("NEW", False, "new material finding", key)
