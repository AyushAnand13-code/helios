"""Memory — the state that makes the autonomous run smart instead of spammy (principle #5).

- seasonality.py : a calendar of known seasonal events so expected moves aren't alerted.
- store.py       : a durable record of prior diagnoses (save_diagnosis / recall_prior).
- suppression.py : the decision — ship a NEW finding, or suppress a SEASONAL / REPEAT /
                   REFUTED / IMMATERIAL one.

Together they let a daily run re-diagnose without re-paging the team on the same finding.
"""
from .store import MemoryStore, DiagnosisRecord, finding_key  # noqa: F401
from .seasonality import SeasonalityCalendar, DEFAULT_CALENDAR  # noqa: F401
from .suppression import decide, SuppressionDecision  # noqa: F401
