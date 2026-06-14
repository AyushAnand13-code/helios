"""Scenario injector — perturb a real baseline segment table with a KNOWN cause.

Each scenario produces a (t0, t1) segment table in decompose_change format
({segment, num_t0, den_t0, num_t1, den_t1}) plus the ground truth: which segment was
perturbed and whether the injected effect was a 'rate' change or a 'mix' shift.

- RATE injection: scale a segment's purchasers only -> its conversion RATE moves; weights
  barely move. The honest cause is that segment, effect = 'rate'.
- MIX injection: scale a segment's sessions AND purchasers together -> its RATE is
  unchanged but its share of traffic (weight) moves -> the aggregate shifts purely by
  composition. The honest cause is that segment, effect = 'mix'. A naive "which segment's
  rate moved most" baseline is blind to this (no rate moved anywhere).
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Scenario:
    name: str
    segments: list          # [{segment, num_t0, den_t0, num_t1, den_t1}, ...]
    truth_segment: str
    truth_effect: str       # 'rate' | 'mix'


def _build(base: list, target: str, num_mult: float, den_mult: float) -> list:
    out = []
    for s in base:
        hit = s["segment"] == target
        out.append({
            "segment": s["segment"],
            "num_t0": float(s["num"]), "den_t0": float(s["den"]),
            "num_t1": float(s["num"]) * (num_mult if hit else 1.0),
            "den_t1": float(s["den"]) * (den_mult if hit else 1.0),
        })
    return out


def inject_rate(base: list, target: str, rate_mult: float) -> Scenario:
    """Scale only the target segment's purchasers -> a rate change in that segment."""
    return Scenario(f"rate {target} x{rate_mult:g}",
                    _build(base, target, num_mult=rate_mult, den_mult=1.0),
                    target, "rate")


def inject_mix(base: list, target: str, vol_mult: float) -> Scenario:
    """Scale the target segment's sessions AND purchasers equally -> a pure mix shift
    (its rate is unchanged; only its weight in the traffic moves)."""
    return Scenario(f"mix {target} x{vol_mult:g}",
                    _build(base, target, num_mult=vol_mult, den_mult=vol_mult),
                    target, "mix")


def make_scenarios(base: list) -> list:
    """Build a balanced benchmark from the largest real segments: 4 rate-change and
    4 mix-shift injections with clean, known ground truth."""
    ranked = sorted([s for s in base if s["den"] > 0], key=lambda s: s["den"], reverse=True)
    if len(ranked) < 4:
        raise ValueError("need at least 4 non-empty segments to build the benchmark")
    t = [s["segment"] for s in ranked[:4]]
    return [
        inject_rate(base, t[0], 0.60),   # 40% rate drop in the biggest segment
        inject_rate(base, t[1], 0.70),
        inject_rate(base, t[2], 1.40),   # a rate rise
        inject_rate(base, t[3], 0.50),
        inject_mix(base, t[0], 2.00),    # double a segment's traffic (composition shift)
        inject_mix(base, t[1], 0.40),    # shrink a segment's traffic
        inject_mix(base, t[2], 1.80),
        inject_mix(base, t[3], 0.45),
    ]
