"""experiment-mcp — powered experiment design as MCP tools (Bible section 18; principle #4).

Wraps helios.experiment so an MCP client sizes a defensible A/B test for a finding instead
of guessing a sample size in prose. Deterministic (scipy); the same two-proportion math the
result will later be judged by.

Tools: power_analysis, runtime_estimate, design_experiment.
Run:   python -m helios.mcp.experiment
"""
from __future__ import annotations

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:  # pragma: no cover
    raise SystemExit("mcp SDK not installed. Run: pip install 'mcp>=1.0'") from e

from helios.experiment import required_sample_size, runtime_days, design_experiment

mcp = FastMCP("experiment-mcp")


@mcp.tool()
def power_analysis(baseline_rate: float, mde_rel: float,
                   alpha: float = 0.05, power: float = 0.80) -> dict:
    """Sample size PER ARM to detect a relative lift `mde_rel` (e.g. 0.05 = +5%) on
    `baseline_rate` in a two-sided two-proportion test at the given alpha and power."""
    try:
        n = required_sample_size(baseline_rate, mde_rel, alpha, power)
    except ValueError as e:
        return {"error": str(e)}
    return {"n_per_arm": n, "baseline_rate": baseline_rate, "mde_rel": mde_rel,
            "alpha": alpha, "power": power}


@mcp.tool()
def runtime_estimate(n_per_arm: int, daily_eligible_sessions: float, arms: int = 2) -> dict:
    """Calendar days to enroll n_per_arm * arms sessions at the given daily eligible
    traffic."""
    days = runtime_days(n_per_arm, daily_eligible_sessions, arms)
    return {"total_n": n_per_arm * arms, "runtime_days": days,
            "runtime_weeks": round(days / 7, 1) if days is not None else None}


@mcp.tool(name="design_experiment")
def design_experiment_tool(primary_metric: str, segment: str, baseline_rate: float,
                           daily_eligible_sessions: float, mde_rel: float = 0.05,
                           alpha: float = 0.05, power: float = 0.80) -> dict:
    """Compose a full powered A/B test spec (hypothesis, primary metric, guardrails,
    sample size, runtime, feasibility) for a finding on `segment`."""
    try:
        return design_experiment(
            primary_metric=primary_metric, segment=segment, baseline_rate=baseline_rate,
            daily_eligible_sessions=daily_eligible_sessions, mde_rel=mde_rel,
            alpha=alpha, power=power).to_dict()
    except ValueError as e:
        return {"error": str(e)}


def main() -> None:
    """Run the stdio MCP server (entry point for `python -m helios.mcp.experiment`)."""
    mcp.run()


if __name__ == "__main__":
    main()
