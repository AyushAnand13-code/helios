"""report-mcp — diagnosis memory as MCP tools (Bible section 18).

Wraps helios.memory so an MCP client can persist findings and ask "have we seen this
before / is it seasonal?" — the state that keeps the autonomous run from re-paging the
team. Backed by a JSONL store (path from HELIOS_MEMORY_PATH, default memory/diagnoses.jsonl).

Tools: save_diagnosis, recall_prior, check_suppression.
Run:   python -m helios.mcp.report
"""
from __future__ import annotations
import os
from dataclasses import asdict
from types import SimpleNamespace

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:  # pragma: no cover
    raise SystemExit("mcp SDK not installed. Run: pip install 'mcp>=1.0'") from e

from helios.memory import MemoryStore, DiagnosisRecord, decide, DEFAULT_CALENDAR

mcp = FastMCP("report-mcp")
_store = MemoryStore(os.environ.get("HELIOS_MEMORY_PATH", "memory/diagnoses.jsonl"))


@mcp.tool()
def save_diagnosis(as_of: str, w0: str, w1: str, dominant: str, segment: str,
                   delta: float, revenue_at_risk: float, verdict: str) -> dict:
    """Persist a reported finding so future runs can recognise a repeat. Returns the
    stored record including its finding `key` (dominant|segment|direction)."""
    from helios.memory.store import finding_key
    rec = DiagnosisRecord(
        as_of=as_of, w0=w0, w1=w1, key=finding_key(dominant, segment, delta),
        dominant=dominant, segment=segment, direction="down" if delta < 0 else "up",
        delta=delta, revenue_at_risk=revenue_at_risk, verdict=verdict)
    _store.save_diagnosis(rec)
    return asdict(rec)


@mcp.tool()
def recall_prior(key: str, as_of: str | None = None, within_days: int | None = None) -> dict:
    """Recall prior findings with this fingerprint `key`, most recent first (optionally
    only those within `within_days` before `as_of`)."""
    recs = _store.recall_prior(key, as_of=as_of, within_days=within_days)
    return {"count": len(recs), "records": [asdict(r) for r in recs]}


@mcp.tool()
def check_suppression(dominant: str, top_segment: str, delta: float, w1: str,
                      verdict: str, as_of: str) -> dict:
    """Decide whether a finding should ALERT or be suppressed (SEASONAL / REFUTED /
    IMMATERIAL / REPEAT) given memory + the seasonality calendar. `w1` is the compare
    week start; `verdict` is the Critic verdict."""
    diag = SimpleNamespace(dominant=dominant, delta=delta, w0="", w1=w1,
                           drivers=[{"segment": top_segment}], revenue_at_risk=0.0)
    report = SimpleNamespace(verdict=verdict, failures=[])
    dec = decide(diag, report, as_of=as_of, store=_store, calendar=DEFAULT_CALENDAR)
    return {"status": dec.status, "suppress": dec.suppress, "reason": dec.reason, "key": dec.key}


def main() -> None:
    """Run the stdio MCP server (entry point for `python -m helios.mcp.report`)."""
    mcp.run()


if __name__ == "__main__":
    main()
