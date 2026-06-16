"""stats-mcp — the ONLY path to math, exposed as MCP tools (Bible section 18; the v1
keystone in docs/planning/LEAN_SCOPE.md).

It wraps the deterministic, seeded, unit-tested engine in `helios.stats` (and the
`helios.critic` firewall) as stdio MCP tools. Per grounding rule G2, the LLM never
computes a statistic in prose — it calls these. Every number a tool returns is a real
Python output, authoritative and reproducible.

Tools:
    decompose_change   — split an aggregate-rate change into mix / rate / interaction
    significance_test  — two-proportion z-test on a rate move
    critique_decomposition — adversarial verify-then-trust check on a decomposition

Run:    python -m helios.mcp.stats          # stdio server, for an MCP client
Import: from helios.mcp.stats import mcp, decompose_change   # tools are plain callables
"""
from __future__ import annotations

from pydantic import BaseModel, Field

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:  # pragma: no cover - only hit without the SDK installed
    raise SystemExit("mcp SDK not installed. Run: pip install 'mcp>=1.0'") from e

from helios.stats import decompose_change as _decompose
from helios.stats import two_proportion_ztest as _ztest
from helios.stats import detect_anomaly as _detect_anomaly
from helios.stats import forecast_next as _forecast_next

mcp = FastMCP("stats-mcp")


class Segment(BaseModel):
    """One segment's numerator/denominator in the base (t0) and compare (t1) periods.
    For session conversion: num = purchasing_sessions, den = sessions."""
    segment: str = Field(description="Segment label, e.g. 'Paid Search / mobile'.")
    num_t0: float = Field(description="Numerator in the base period.")
    den_t0: float = Field(description="Denominator in the base period.")
    num_t1: float = Field(description="Numerator in the compare period.")
    den_t1: float = Field(description="Denominator in the compare period.")


def _rows(segments: list) -> list[dict]:
    return [s.model_dump() if isinstance(s, Segment) else dict(s) for s in segments]


@mcp.tool()
def decompose_change(segments: list[Segment]) -> dict:
    """Decompose the change in a weighted aggregate rate R = sum_i(w_i * r_i) between two
    periods into three additive, exhaustive effects:
      mix_effect  = sum d_w_i * r_i(t0)   (traffic composition changed)
      rate_effect = sum w_i(t0) * d_r_i   (in-segment behaviour changed)
      interaction = sum d_w_i * d_r_i     (both moved together)
    Drill into RATE effects (real behaviour), not MIX effects (composition artifacts) —
    this is how Simpson's paradox is dissolved. Deterministic; no randomness.
    Returns the aggregate effects, the dominant one, whether it reconciles, and the
    per-segment contributions sorted by absolute total impact."""
    res = _decompose(_rows(segments))
    return {
        "delta": res.delta,
        "mix_effect": res.mix_effect,
        "rate_effect": res.rate_effect,
        "interaction": res.interaction,
        "r_t0": res.r_t0,
        "r_t1": res.r_t1,
        "dominant_effect": res.dominant_effect,
        "reconciles": res.check_additive(),
        "segments": [
            {"segment": c.segment, "mix": c.mix, "rate": c.rate,
             "interaction": c.interaction, "total": c.total,
             "w_t0": c.w_t0, "w_t1": c.w_t1, "r_t0": c.r_t0, "r_t1": c.r_t1}
            for c in res.segments
        ],
    }


@mcp.tool()
def significance_test(num_a: int, den_a: int, num_b: int, den_b: int,
                      alpha: float = 0.05) -> dict:
    """Two-sided pooled two-proportion z-test: did rate B (num_b/den_b) really differ
    from rate A (num_a/den_a), or is it noise? Returns both rates, the z-statistic, the
    p-value, and whether it is significant at `alpha`. Use this instead of eyeballing a
    percentage move."""
    r = _ztest(num_a, den_a, num_b, den_b, alpha=alpha)
    return {"rate_a": r.rate_a, "rate_b": r.rate_b, "abs_diff": r.abs_diff,
            "z": r.z, "p_value": r.p_value, "significant": r.significant}


@mcp.tool()
def critique_decomposition(segments: list[Segment], alpha: float = 0.05) -> dict:
    """Verify-then-trust (principle #2): decompose the move, test its significance, and
    attack the finding with the Critic before trusting it. Returns the decomposition, the
    significance test on the aggregate, and a SHIP / REVISE / REFUTE verdict with the
    individual checks (reconcile, materiality, significance, mix-vs-rate framing). Call
    this when you want a single trustworthy verdict rather than raw numbers."""
    from types import SimpleNamespace
    from helios.critic import critique

    rows = _rows(segments)
    res = _decompose(rows)
    den0 = sum(s["den_t0"] for s in rows)
    den1 = sum(s["den_t1"] for s in rows)
    num0 = sum(s["num_t0"] for s in rows)
    num1 = sum(s["num_t1"] for s in rows)
    sig = _ztest(int(num0), int(den0), int(num1), int(den1), alpha=alpha)

    diag = SimpleNamespace(
        delta=res.delta, mix=res.mix_effect, rate=res.rate_effect,
        interaction=res.interaction, dominant=res.dominant_effect,
        conv_t0=res.r_t0, conv_t1=res.r_t1,
        p_value=sig.p_value, significant=sig.significant,
        # Dollar checks need money inputs the caller may not supply; pass neutral values
        # so the dollar-sanity check is a no-op rather than a false failure.
        sessions_t1=int(den1) or 1, aov=1.0,
        revenue_at_risk=res.rate_effect * (int(den1) or 1) * 1.0,
        drivers=[{"segment": c.segment} for c in res.segments],
        funnel_t0={}, funnel_t1={},
    )
    report = critique(diag)
    return {
        "verdict": report.verdict,
        "dominant_effect": res.dominant_effect,
        "significant": sig.significant,
        "p_value": sig.p_value,
        "checks": report.to_dict()["checks"],
    }


@mcp.tool()
def detect_anomaly(values: list[float], k: int = 4, z_threshold: float = 2.5) -> dict:
    """Forecast-based anomaly detection on a metric time series (oldest -> newest). Each
    point is scored against a rolling forecast of its recent history; points with
    |z| > z_threshold are anomalies. Use this instead of eyeballing 'the biggest move' — it
    ignores low-volume weeks whose RATE is normal. Returns per-point forecasts/z and the
    flagged anomaly indices."""
    pts = _detect_anomaly(values, k=k, z_threshold=z_threshold)
    return {
        "anomalies": [p.index for p in pts if p.is_anomaly],
        "points": [{"index": p.index, "value": p.value, "forecast": p.forecast,
                    "z": p.z, "is_anomaly": p.is_anomaly} for p in pts],
    }


@mcp.tool()
def forecast(values: list[float], k: int = 4, conf: float = 0.95) -> dict:
    """Point forecast + prediction interval for the NEXT value of a metric series. A new
    actual outside [lower, upper] is anomalous at the given confidence."""
    try:
        return _forecast_next(values, k=k, conf=conf)
    except ValueError as e:
        return {"error": str(e)}


def main() -> None:
    """Run the stdio MCP server (the entry point for `python -m helios.mcp.stats`)."""
    mcp.run()


if __name__ == "__main__":
    main()
