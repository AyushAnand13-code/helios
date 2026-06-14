"""Honest offline eval: inject known funnel anomalies, check whether the mix-vs-rate
decomposition recovers the true cause, and compare against a naive baseline.

Framed as CONTROLLED-ATTRIBUTION accuracy (not causal): we know the injected cause by
construction, so we can score whether each method attributes the move to the right
segment and the right kind of effect (mix vs rate)."""
from .injector import make_scenarios, Scenario  # noqa: F401
from .baselines import naive_largest_delta  # noqa: F401
from .runner import score_benchmark, load_base_segments, BenchmarkResult  # noqa: F401
