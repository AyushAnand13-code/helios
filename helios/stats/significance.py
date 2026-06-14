"""Two-proportion significance test — deterministic, for funnel-rate comparisons.

Answers "did this segment's conversion rate REALLY move, or is it noise?" using a
two-sided two-proportion z-test (pooled). No randomness, no seed needed.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
from scipy import stats


@dataclass
class SignificanceResult:
    rate_a: float
    rate_b: float
    z: float
    p_value: float
    significant: bool

    @property
    def abs_diff(self) -> float:
        return abs(self.rate_b - self.rate_a)


def two_proportion_ztest(num_a: int, den_a: int, num_b: int, den_b: int,
                         alpha: float = 0.05) -> SignificanceResult:
    """Pooled two-sided two-proportion z-test between period A and period B."""
    if den_a <= 0 or den_b <= 0:
        raise ValueError("denominators must be positive")
    p_a = num_a / den_a
    p_b = num_b / den_b
    p_pool = (num_a + num_b) / (den_a + den_b)
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / den_a + 1 / den_b))
    if se == 0:
        z = 0.0
        p_value = 1.0
    else:
        z = (p_b - p_a) / se
        p_value = 2 * (1 - stats.norm.cdf(abs(z)))
    return SignificanceResult(
        rate_a=p_a, rate_b=p_b, z=z, p_value=p_value, significant=p_value < alpha,
    )
