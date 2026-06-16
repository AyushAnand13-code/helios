"""design_experiment — compose a full, powered experiment spec from a finding.

Given the segment, its baseline rate, and its eligible daily traffic, it sizes a two-arm
test (via power.py) and packages the hypothesis, primary metric, guardrails, sample size,
and runtime. This is what turns a Helios finding into something a growth team can actually
launch — satisfying principle #4 ("a finding without a recommended action is not a
finding").
"""
from __future__ import annotations
from dataclasses import dataclass, asdict

from .power import required_sample_size, runtime_days

# Sensible default guardrails to protect while chasing a conversion lift.
DEFAULT_GUARDRAILS = ["aov", "cart_abandonment_rate", "net_revenue"]


@dataclass
class ExperimentDesign:
    hypothesis: str
    segment: str
    primary_metric: str
    guardrails: list[str]
    baseline_rate: float
    mde_rel: float
    alpha: float
    power: float
    arms: int
    split: str
    n_per_arm: int
    total_n: int
    daily_eligible_sessions: float
    runtime_days: int | None
    runtime_weeks: float | None
    feasible: bool

    def to_dict(self) -> dict:
        return asdict(self)


def design_experiment(*, primary_metric: str, segment: str, baseline_rate: float,
                      daily_eligible_sessions: float, mde_rel: float = 0.05,
                      alpha: float = 0.05, power: float = 0.80, arms: int = 2,
                      guardrails: list[str] | None = None,
                      max_runtime_days: int = 42) -> ExperimentDesign:
    """Size a powered A/B test to detect a `mde_rel` lift in `primary_metric` for `segment`.
    `daily_eligible_sessions` is that segment's typical daily traffic. `feasible` is False
    if the runtime exceeds `max_runtime_days` (or there's no eligible traffic)."""
    guardrails = guardrails or list(DEFAULT_GUARDRAILS)
    n_per_arm = required_sample_size(baseline_rate, mde_rel, alpha, power)
    total_n = n_per_arm * arms
    days = runtime_days(n_per_arm, daily_eligible_sessions, arms)
    weeks = round(days / 7, 1) if days is not None else None
    feasible = days is not None and days <= max_runtime_days

    hypothesis = (f"A targeted change for '{segment}' lifts {primary_metric} by at least "
                  f"{mde_rel * 100:.0f}% (from a {baseline_rate * 100:.2f}% baseline).")
    return ExperimentDesign(
        hypothesis=hypothesis, segment=segment, primary_metric=primary_metric,
        guardrails=guardrails, baseline_rate=baseline_rate, mde_rel=mde_rel,
        alpha=alpha, power=power, arms=arms, split="/".join(["50"] * arms) if arms == 2
        else f"{round(100/arms)}% x {arms}",
        n_per_arm=n_per_arm, total_n=total_n,
        daily_eligible_sessions=daily_eligible_sessions,
        runtime_days=days, runtime_weeks=weeks, feasible=feasible)
