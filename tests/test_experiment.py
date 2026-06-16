"""Experiment design tests — power/runtime math + the composed spec. Pure-Python (scipy).
Run: pytest tests/test_experiment.py -v
"""
import pytest

from helios.experiment import required_sample_size, runtime_days, design_experiment


def test_sample_size_matches_known_value():
    # Baseline 2%, detect +10% relative (2.0% -> 2.2%), alpha 0.05, power 0.8.
    # Standard two-proportion formula gives ~80-82k per arm; pin a tight band.
    n = required_sample_size(0.02, 0.10, alpha=0.05, power=0.80)
    assert 78_000 <= n <= 86_000


def test_smaller_effect_needs_more_samples():
    assert required_sample_size(0.02, 0.05) > required_sample_size(0.02, 0.10)


def test_higher_power_needs_more_samples():
    assert (required_sample_size(0.02, 0.10, power=0.9)
            > required_sample_size(0.02, 0.10, power=0.8))


def test_degenerate_inputs_raise():
    with pytest.raises(ValueError):
        required_sample_size(0.0, 0.1)
    with pytest.raises(ValueError):
        required_sample_size(0.02, 0.0)


def test_runtime_scales_with_traffic():
    assert runtime_days(10_000, 1_000, arms=2) == 20      # 20k / 1k
    assert runtime_days(10_000, 0) is None


def test_design_experiment_is_complete_and_feasible():
    d = design_experiment(primary_metric="session_conversion_rate",
                          segment="Paid Search / mobile", baseline_rate=0.03,
                          daily_eligible_sessions=20_000, mde_rel=0.10)
    assert d.primary_metric == "session_conversion_rate"
    assert d.n_per_arm > 0 and d.total_n == 2 * d.n_per_arm
    assert d.runtime_days is not None and d.runtime_weeks is not None
    assert d.feasible is True
    assert "aov" in d.guardrails
    assert "Paid Search / mobile" in d.hypothesis


def test_design_flags_infeasible_when_traffic_is_thin():
    d = design_experiment(primary_metric="session_conversion_rate", segment="Email / tablet",
                          baseline_rate=0.02, daily_eligible_sessions=50, mde_rel=0.05)
    assert d.feasible is False   # tiny traffic -> runtime blows past the cap
