"""report-mcp smoke tests — save/recall round-trip and the suppression decision over MCP.
Skipped where the `mcp` SDK is absent (lean CI image). Run: pytest tests/test_mcp_report.py -v
"""
import asyncio

import pytest

pytest.importorskip("mcp")


def test_tools_registered_and_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("HELIOS_MEMORY_PATH", str(tmp_path / "m.jsonl"))
    import importlib
    import helios.mcp.report as report
    importlib.reload(report)   # rebind the module-level store to the temp path

    names = {t.name for t in asyncio.run(report.mcp.list_tools())}
    assert names == {"save_diagnosis", "recall_prior", "check_suppression"}

    saved = report.save_diagnosis(as_of="2020-12-07", w0="2020-11-30", w1="2020-12-07",
                                  dominant="rate", segment="Referral / desktop",
                                  delta=-0.012, revenue_at_risk=-40_000.0, verdict="SHIP")
    key = saved["key"]
    assert report.recall_prior(key)["count"] == 1

    # next-day identical finding -> REPEAT
    dec = report.check_suppression(dominant="rate", top_segment="Referral / desktop",
                                   delta=-0.012, w1="2020-12-07", verdict="SHIP",
                                   as_of="2020-12-08")
    assert dec["status"] == "REPEAT" and dec["suppress"] is True

    # a seasonal week -> SEASONAL regardless of memory
    seasonal = report.check_suppression(dominant="rate", top_segment="X / y", delta=-0.02,
                                        w1="2020-11-23", verdict="SHIP", as_of="2020-11-30")
    assert seasonal["status"] == "SEASONAL"
