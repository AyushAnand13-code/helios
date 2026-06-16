"""semantic-mcp — the only path to SQL, exposed as MCP tools (Bible section 18; grounding
rules G1 + G5).

Wraps helios.semantic.SemanticLayer so an MCP client (Claude Code) composes governed SQL
from the registry instead of hand-authoring it. Unknown metric/dimension names, dimensions
a metric doesn't support, and mixed grains all come back as tool errors — there is no path
to free SQL.

Tools:
    get_metric        — the governed definition of a metric
    list_metrics      — all governed metric names
    list_dimensions   — all governed dimension names
    build_query       — compose a governed SELECT from metrics + dimensions (+ filters)

Run:    python -m helios.mcp.semantic
Import: from helios.mcp.semantic import mcp, build_query
"""
from __future__ import annotations

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:  # pragma: no cover
    raise SystemExit("mcp SDK not installed. Run: pip install 'mcp>=1.0'") from e

from helios.semantic import SemanticLayer, SemanticError

mcp = FastMCP("semantic-mcp")
_layer = SemanticLayer()   # loads semantic/semantic_layer.yaml


@mcp.tool()
def list_metrics() -> list[str]:
    """List every governed metric name. Use these EXACT names — an unknown name is a
    hard error, never a fallback to free SQL."""
    return _layer.list_metrics()


@mcp.tool()
def list_dimensions() -> list[str]:
    """List every governed dimension name available for grouping/filtering."""
    return _layer.list_dimensions()


@mcp.tool()
def get_metric(name: str) -> dict:
    """Return the governed definition of a metric (business definition, SQL definition,
    grain, supported dimensions, caveats). Call this to ground a term instead of guessing."""
    try:
        m = _layer.get_metric(name)
    except SemanticError as e:
        return {"error": str(e)}
    return {k: m.get(k) for k in ("metric_name", "label", "type", "sql_definition",
                                  "grain", "business_definition", "dimensions_supported",
                                  "numerator", "denominator", "caveats")}


@mcp.tool()
def build_query(metrics: list[str], dimensions: list[str] | None = None,
                filters: list[dict] | None = None,
                project: str | None = None, dataset: str = "helios_dev_marts") -> dict:
    """Compose a GOVERNED SQL SELECT for the given metrics grouped by the given dimensions
    (optionally filtered). The SQL is assembled only from registered definitions — never
    hand-typed. `filters` is a list of {dimension, op, value} (op one of =, !=, >, >=, <,
    <=, IN, NOT IN, BETWEEN; value a scalar, a list for IN, or [lo, hi] for BETWEEN).
    Returns {sql} or {error} on any governance violation."""
    try:
        sql = _layer.build_query(metrics, dimensions, filters,
                                 project=project, dataset=dataset)
    except SemanticError as e:
        return {"error": str(e)}
    return {"sql": sql, "grain": _layer.get_metric(metrics[0])["grain"]}


def main() -> None:
    """Run the stdio MCP server (entry point for `python -m helios.mcp.semantic`)."""
    mcp.run()


if __name__ == "__main__":
    main()
