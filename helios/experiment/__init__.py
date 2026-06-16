"""Experiment design — turn a finding into a powered, sized A/B test (principle #4:
"every finding is actionable"). Deterministic stats only (scipy), never token-space math.

- power.py  : required sample size + runtime for a two-proportion test.
- design.py : compose a full experiment spec (hypothesis, primary metric, guardrails,
              sample size, runtime) from a finding.
"""
from .power import required_sample_size, runtime_days  # noqa: F401
from .design import design_experiment, ExperimentDesign  # noqa: F401
