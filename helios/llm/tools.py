"""Governed tools the LLM is allowed to call.

Each tool wraps deterministic logic (the mix/rate engine, the significance test) or the
governed metric registry. The LLM composes these; it never authors SQL or computes a
statistic itself (grounding rules G1/G2). Every tool logs its call so the brief can
prove which governed outputs it was built from.
"""
from __future__ import annotations
from pathlib import Path

import yaml

from helios.diagnosis import weeks_in, biggest_move, run_diagnosis


def _r(x: float, n: int = 4) -> float:
    return round(float(x), n)


class GovernedTools:
    """Holds the loaded funnel data + metric registry and exposes the callable tools.

    Pass a pre-loaded weekly DataFrame (from helios.diagnosis.load_weekly) and the path
    to models/semantic/semantic_layer.yaml.
    """

    def __init__(self, df, registry_path: str | Path):
        self.df = df
        reg = yaml.safe_load(Path(registry_path).read_text(encoding="utf-8"))
        self._metrics = {m["metric_name"]: m for m in (reg.get("metrics") or [])}
        self.calls: list[str] = []   # grounding log

    # ---- tools (these become the model's callable functions) ----

    def list_available_weeks(self) -> dict:
        """List the weeks available for analysis (Monday-anchored 'YYYY-MM-DD' starts)
        and the week-pair with the single biggest week-over-week conversion move.
        Call this FIRST to choose which weeks to diagnose."""
        weeks = weeks_in(self.df)
        a, b = biggest_move(self.df)
        self.calls.append(f"list_available_weeks() -> {len(weeks)} weeks, biggest move {a}->{b}")
        return {"weeks": weeks, "suggested_biggest_move": {"baseline": a, "compare": b}}

    def diagnose_conversion_change(self, week_baseline: str, week_compare: str) -> dict:
        """Diagnose the change in SESSION CONVERSION between two weeks. week_baseline and
        week_compare must be 'YYYY-MM-DD' week-start values from list_available_weeks.
        Returns the deterministic mix-vs-rate decomposition (mix = traffic composition
        changed, rate = in-segment behaviour changed, interaction = both), a two-proportion
        significance test, dollars of revenue-at-risk, and the top driver segments. All
        numbers here are computed in real Python — treat them as authoritative."""
        d = run_diagnosis(self.df, week_baseline, week_compare)
        self.calls.append(f"diagnose_conversion_change({week_baseline}, {week_compare})")
        return {
            "week_baseline": d.w0,
            "week_compare": d.w1,
            "conversion_baseline_pct": _r(d.conv_t0 * 100, 3),
            "conversion_compare_pct": _r(d.conv_t1 * 100, 3),
            "delta_points": _r(d.delta * 100, 3),
            "mix_effect_points": _r(d.mix * 100, 3),
            "rate_effect_points": _r(d.rate * 100, 3),
            "interaction_points": _r(d.interaction * 100, 3),
            "dominant_effect": d.dominant,
            "p_value": _r(d.p_value, 6),
            "statistically_significant": bool(d.significant),
            "sessions_compare_week": int(d.sessions_t1),
            "aov_usd": _r(d.aov, 2),
            "revenue_at_risk_usd": _r(d.revenue_at_risk, 0),
            "top_driver_segments": [
                {
                    "segment": x["segment"],
                    "total_contribution_points": _r(x["total_pts"], 3),
                    "mix_points": _r(x["mix_pts"], 3),
                    "rate_points": _r(x["rate_pts"], 3),
                    "conversion_before_pct": _r(x["conv_t0_pct"], 3),
                    "conversion_after_pct": _r(x["conv_t1_pct"], 3),
                }
                for x in d.drivers[:5]
            ],
        }

    def get_metric_definition(self, metric_name: str) -> dict:
        """Look up the GOVERNED definition of a metric by its exact snake_case name (e.g.
        'session_conversion_rate', 'revenue', 'aov'). Use this instead of guessing what a
        metric means. Returns the business definition, SQL definition, and caveats, or an
        error listing valid names if the metric is unknown."""
        self.calls.append(f"get_metric_definition({metric_name})")
        m = self._metrics.get(metric_name)
        if not m:
            return {"error": f"'{metric_name}' is not a governed metric.",
                    "known_metrics": sorted(self._metrics)[:40]}
        return {
            "metric_name": metric_name,
            "label": m.get("label"),
            "business_definition": m.get("business_definition"),
            "sql_definition": m.get("sql_definition"),
            "caveats": m.get("caveats"),
        }

    # Explicit function-call schemas (we declare these instead of relying on the SDK's
    # signature introspection, which is brittle for parameterized tools).
    DECLARATIONS = [
        {
            "name": "list_available_weeks",
            "description": ("List the weeks available for analysis (Monday-anchored "
                            "'YYYY-MM-DD' starts) and the week-pair with the biggest "
                            "week-over-week conversion move. Call this FIRST."),
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "diagnose_conversion_change",
            "description": ("Diagnose the change in SESSION CONVERSION between two weeks. "
                            "Returns the mix-vs-rate decomposition, significance, "
                            "revenue-at-risk, and top driver segments. All numbers are "
                            "computed deterministically — treat them as authoritative."),
            "parameters": {
                "type": "object",
                "properties": {
                    "week_baseline": {"type": "string",
                                      "description": "Baseline week start, 'YYYY-MM-DD'."},
                    "week_compare": {"type": "string",
                                     "description": "Compare week start, 'YYYY-MM-DD'."},
                },
                "required": ["week_baseline", "week_compare"],
            },
        },
        {
            "name": "get_metric_definition",
            "description": ("Look up the governed definition of a metric by its exact "
                            "snake_case name (e.g. 'session_conversion_rate', 'aov')."),
            "parameters": {
                "type": "object",
                "properties": {
                    "metric_name": {"type": "string",
                                    "description": "Exact snake_case metric name."},
                },
                "required": ["metric_name"],
            },
        },
    ]

    def dispatch(self, name: str, args: dict):
        """Execute a tool call by name. Returns the tool's result dict (or an error dict)."""
        fn = {
            "list_available_weeks": self.list_available_weeks,
            "diagnose_conversion_change": self.diagnose_conversion_change,
            "get_metric_definition": self.get_metric_definition,
        }.get(name)
        if fn is None:
            return {"error": f"unknown tool '{name}'"}
        try:
            return fn(**(args or {}))
        except Exception as e:  # noqa: BLE001
            return {"error": f"{type(e).__name__}: {e}"}
