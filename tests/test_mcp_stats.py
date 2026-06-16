"""stats-mcp smoke tests — the MCP wrapper must register its tools and return the same
numbers as the underlying deterministic engine. Skipped automatically where the `mcp`
SDK isn't installed (e.g. the lean CI image). Run: pytest tests/test_mcp_stats.py -v
"""
import asyncio

import pytest

pytest.importorskip("mcp")  # the stats-mcp wrapper needs the MCP SDK + pydantic

from helios.mcp.stats import (mcp, decompose_change, significance_test,  # noqa: E402
                              critique_decomposition)
from helios.stats import decompose_change as engine_decompose  # noqa: E402

SEGS = [
    {"segment": "A", "num_t0": 25, "den_t0": 500, "num_t1": 22.0, "den_t1": 440},
    {"segment": "B", "num_t0": 10, "den_t0": 500, "num_t1": 11.2, "den_t1": 560},
]


def test_tools_are_registered():
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert names == {"decompose_change", "significance_test", "critique_decomposition"}


def test_decompose_matches_engine_and_golden():
    out = decompose_change(SEGS)
    ref = engine_decompose(SEGS)
    assert out["mix_effect"] == pytest.approx(ref.mix_effect)
    assert out["dominant_effect"] == ref.dominant_effect == "mix"
    assert out["reconciles"] is True
    assert abs(out["mix_effect"] + 0.0018) < 1e-9          # pinned golden value


def test_significance_tool():
    out = significance_test(300, 10000, 250, 10000)
    assert out["significant"] is True
    assert out["p_value"] < 0.05


def test_critique_tool_returns_a_verdict():
    out = critique_decomposition(SEGS)
    assert out["verdict"] in {"SHIP", "REVISE", "REFUTE"}
    assert out["dominant_effect"] == "mix"
