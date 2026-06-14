"""decompose_change — the technical centerpiece of Helios.

Splits the change in an aggregate rate R = sum_i (w_i * r_i) between two periods
(t0 -> t1) into three additive, exhaustive effects:

    mix_effect   = sum_i  d_w_i * r_i(t0)      # traffic composition changed
    rate_effect  = sum_i  w_i(t0) * d_r_i      # in-segment behaviour changed
    interaction  = sum_i  d_w_i * d_r_i        # both moved together
    delta_R      = mix_effect + rate_effect + interaction = R(t1) - R(t0)

This is how Simpson's paradox is dissolved: drill into RATE effects (real behaviour
change), not MIX effects (composition artifacts). Deterministic — no randomness, no seed.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Sequence, Mapping


@dataclass
class SegmentContribution:
    segment: str
    mix: float
    rate: float
    interaction: float
    w_t0: float
    w_t1: float
    r_t0: float
    r_t1: float

    @property
    def total(self) -> float:
        return self.mix + self.rate + self.interaction


@dataclass
class DecompositionResult:
    delta: float                 # R(t1) - R(t0)
    mix_effect: float
    rate_effect: float
    interaction: float
    r_t0: float
    r_t1: float
    segments: list[SegmentContribution] = field(default_factory=list)

    @property
    def dominant_effect(self) -> str:
        """Which of mix / rate / interaction explains the most of the move."""
        effects = {"mix": self.mix_effect, "rate": self.rate_effect, "interaction": self.interaction}
        return max(effects, key=lambda k: abs(effects[k]))

    def check_additive(self, tol: float = 1e-9) -> bool:
        return abs((self.mix_effect + self.rate_effect + self.interaction) - self.delta) <= tol


def decompose_change(segments: Sequence[Mapping]) -> DecompositionResult:
    """Decompose the change in a weighted aggregate rate across segments.

    Each segment is a mapping with:
        segment : str        — label
        num_t0, den_t0       — numerator/denominator in the base period
        num_t1, den_t1       — numerator/denominator in the compare period

    Weights are the segment's share of the total denominator in each period;
    rates are num/den within the segment (0 when den == 0).
    """
    tot_den_t0 = float(sum(s["den_t0"] for s in segments))
    tot_den_t1 = float(sum(s["den_t1"] for s in segments))
    if tot_den_t0 == 0 or tot_den_t1 == 0:
        raise ValueError("total denominator is zero in one period; cannot decompose")

    mix = rate = inter = 0.0
    contribs: list[SegmentContribution] = []

    for s in segments:
        den0, den1 = float(s["den_t0"]), float(s["den_t1"])
        w0 = den0 / tot_den_t0
        w1 = den1 / tot_den_t1
        r0 = (s["num_t0"] / den0) if den0 else 0.0
        r1 = (s["num_t1"] / den1) if den1 else 0.0
        dw = w1 - w0
        dr = r1 - r0

        s_mix = dw * r0
        s_rate = w0 * dr
        s_inter = dw * dr
        mix += s_mix
        rate += s_rate
        inter += s_inter

        contribs.append(SegmentContribution(
            segment=str(s["segment"]),
            mix=s_mix, rate=s_rate, interaction=s_inter,
            w_t0=w0, w_t1=w1, r_t0=r0, r_t1=r1,
        ))

    r_t0 = sum(c.w_t0 * c.r_t0 for c in contribs)
    r_t1 = sum(c.w_t1 * c.r_t1 for c in contribs)

    return DecompositionResult(
        delta=r_t1 - r_t0,
        mix_effect=mix, rate_effect=rate, interaction=inter,
        r_t0=r_t0, r_t1=r_t1,
        segments=sorted(contribs, key=lambda c: abs(c.total), reverse=True),
    )
