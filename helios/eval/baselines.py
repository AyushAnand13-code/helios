"""Naive baseline: 'largest-segment-delta'.

Pick the segment whose raw conversion rate moved the most between the two periods.
This is what an analyst does without a mix-vs-rate decomposition — and it is blind to
mix-shifts (where no segment's rate moves at all) and to weighting (a big raw delta in a
tiny segment outranks the real driver). It is the honest 'do nothing clever' comparison.
"""
from __future__ import annotations


def _rate(num, den):
    return (num / den) if den else 0.0


NO_SIGNAL = "(no segment — no rate change detected)"
_EPS = 1e-9


def naive_largest_delta(segments: list) -> str:
    """Return the segment with the largest absolute change in raw conversion rate. If no
    segment's rate moved (e.g. a pure mix-shift), honestly report no signal — the baseline
    is structurally blind to composition changes."""
    best = None
    for s in segments:
        d = abs(_rate(s["num_t1"], s["den_t1"]) - _rate(s["num_t0"], s["den_t0"]))
        if best is None or d > best[0]:
            best = (d, s["segment"])
    if best is None or best[0] < _EPS:
        return NO_SIGNAL
    return best[1]
