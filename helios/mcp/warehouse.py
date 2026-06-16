"""warehouse-mcp — the sole BigQuery client, as MCP tools (Bible section 18; G3 + G4).

Wraps helios.warehouse.Warehouse so an MCP client executes governed SQL safely: dry_run
estimates cost, run_query refuses anything over the byte budget, reconcile checks an
aggregate against a canonical total. The SQL itself must come from semantic-mcp — this
server only estimates, runs, and reconciles.

Needs Application Default Credentials (a read-only BigQuery SA) to actually hit BigQuery.

Tools: dry_run, run_query, reconcile.
Run:   python -m helios.mcp.warehouse
"""
from __future__ import annotations
import os

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:  # pragma: no cover
    raise SystemExit("mcp SDK not installed. Run: pip install 'mcp>=1.0'") from e

from helios.warehouse import Warehouse, BudgetExceeded

mcp = FastMCP("warehouse-mcp")
_wh = Warehouse(project=os.environ.get("HELIOS_PROJECT"))


@mcp.tool()
def dry_run(sql: str) -> dict:
    """Estimate the bytes a query would scan WITHOUT running it (G3). Returns the byte
    count, GiB, the budget, and whether it is within budget. Always dry_run before
    run_query."""
    try:
        return _wh.dry_run(sql)
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"}


@mcp.tool()
def run_query(sql: str) -> dict:
    """Dry-run cost-check (G3) then execute a GOVERNED query (compose it with semantic-mcp's
    build_query first). Refuses to run anything over the byte budget. Returns the rows."""
    try:
        rows = _wh.run_query(sql)
        return {"row_count": len(rows), "rows": rows}
    except BudgetExceeded as e:
        return {"error": str(e), "over_budget": True}
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"}


@mcp.tool()
def reconcile(segment_total: float, canonical_total: float,
              tolerance: float = 0.005, label: str = "metric") -> dict:
    """Reconcile a segmented aggregate against its canonical grand total (G4). Drift above
    `tolerance` (default 0.5%) means the finding does not reconcile and must not ship."""
    return Warehouse.reconcile(segment_total, canonical_total,
                               tolerance=tolerance, label=label)


def main() -> None:
    """Run the stdio MCP server (entry point for `python -m helios.mcp.warehouse`)."""
    mcp.run()


if __name__ == "__main__":
    main()
