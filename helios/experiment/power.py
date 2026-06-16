"""Power analysis for a two-proportion A/B test — deterministic, seeded by nothing.

required_sample_size uses the standard normal-approximation formula for detecting a
difference between two proportions at a given significance (alpha) and power:

    n_per_arm = ( z_{1-α/2}·√(2·p̄·(1-p̄)) + z_{1-β}·√(p1·(1-p1) + p2·(1-p2)) )² / (p2 - p1)²

where p1 is the baseline rate, p2 the rate we want to be able to detect, and
p̄ = (p1+p2)/2. Two-sided. This mirrors the math `stats-mcp.significance_test` later runs
on the result, so the design and the readout are consistent.
"""
from __future__ import annotations
import math

from scipy.stats import norm


def required_sample_size(baseline_rate: float, mde_rel: float,
                         alpha: float = 0.05, power: float = 0.80) -> int:
    """Sample size PER ARM to detect a relative lift `mde_rel` (e.g. 0.05 = +5%) on
    `baseline_rate`, two-sided, at the given alpha and power. Raises on degenerate inputs."""
    if not (0.0 < baseline_rate < 1.0):
        raise ValueError("baseline_rate must be in (0, 1)")
    if mde_rel == 0:
        raise ValueError("mde_rel must be non-zero")
    if not (0.0 < alpha < 1.0) or not (0.0 < power < 1.0):
        raise ValueError("alpha and power must be in (0, 1)")
    p1 = baseline_rate
    p2 = p1 * (1 + mde_rel)
    if not (0.0 < p2 < 1.0):
        raise ValueError(f"mde_rel pushes the target rate out of (0,1): p2={p2:.4f}")

    z_a = norm.ppf(1 - alpha / 2)
    z_b = norm.ppf(power)
    p_bar = (p1 + p2) / 2
    numerator = (z_a * math.sqrt(2 * p_bar * (1 - p_bar))
                 + z_b * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    n = numerator / (p2 - p1) ** 2
    return int(math.ceil(n))


def runtime_days(n_per_arm: int, daily_eligible_sessions: float, arms: int = 2) -> int | None:
    """Calendar days to enroll `n_per_arm * arms` sessions given the eligible daily
    traffic. None if there is no eligible traffic."""
    if daily_eligible_sessions <= 0:
        return None
    return int(math.ceil((n_per_arm * arms) / daily_eligible_sessions))
