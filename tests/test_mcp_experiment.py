"""experiment-mcp smoke tests — tool registration + parity with the engine. Skipped where
the `mcp` SDK is absent. Run: pytest tests/test_mcp_experiment.py -v
"""
import asyncio

import pytest

pytest.importorskip("mcp")

from helios.mcp.experiment import (mcp, power_analysis, runtime_estimate,  # noqa: E402
                                   design_experiment_tool)
from helios.experiment import required_sample_size  # noqa: E402


def test_tools_registered_with_canonical_names():
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert names == {"power_analysis", "runtime_estimate", "design_experiment"}


def test_power_analysis_matches_engine():
    out = power_analysis(0.03, 0.10)
    assert out["n_per_arm"] == required_sample_size(0.03, 0.10)


def test_power_analysis_surfaces_bad_input():
    assert "error" in power_analysis(0.0, 0.1)


def test_design_tool_returns_full_spec():
    out = design_experiment_tool("session_conversion_rate", "Direct / desktop", 0.025, 15_000)
    assert out["n_per_arm"] > 0
    assert out["primary_metric"] == "session_conversion_rate"
    assert "runtime_days" in out
