"""semantic-mcp smoke tests — the MCP wrapper must register its tools and return the same
governed SQL as the underlying SemanticLayer. Skipped where the `mcp` SDK is absent (lean
CI image). Run: pytest tests/test_mcp_semantic.py -v
"""
import asyncio

import pytest

pytest.importorskip("mcp")

from helios.mcp.semantic import (mcp, build_query, get_metric,  # noqa: E402
                                 list_metrics, list_dimensions)


def test_tools_are_registered():
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert names == {"build_query", "get_metric", "list_metrics", "list_dimensions"}


def test_build_query_tool_returns_governed_sql():
    out = build_query(["sessions", "purchasing_sessions"], ["week"], dataset="helios_dev")
    assert "error" not in out
    assert "COUNT(DISTINCT session_key) AS sessions" in out["sql"]
    assert out["grain"] == "fct_funnel"


def test_build_query_tool_surfaces_governance_errors():
    out = build_query(["clicks"], ["week"])
    assert "error" in out and "not a governed metric" in out["error"]


def test_get_metric_and_lists():
    assert get_metric("sessions")["sql_definition"] == "COUNT(DISTINCT session_key)"
    assert "error" in get_metric("clicks")
    assert "sessions" in list_metrics()
    assert "channel_group" in list_dimensions()
