"""Run the benchmark: score Helios (mix-vs-rate decomposition) against the naive baseline.

For each injected scenario we know the true cause. Helios predicts the top-contribution
segment AND the dominant effect (mix/rate); the baseline predicts only a segment. We
report controlled-attribution accuracy for each.
"""
from __future__ import annotations
from dataclasses import dataclass, field

from helios.stats import decompose_change
from .injector import make_scenarios
from .baselines import naive_largest_delta


@dataclass
class BenchmarkResult:
    rows: list = field(default_factory=list)          # per-scenario detail
    n: int = 0
    helios_segment_correct: int = 0
    helios_effect_correct: int = 0
    baseline_segment_correct: int = 0

    @property
    def helios_segment_acc(self) -> float:
        return self.helios_segment_correct / self.n if self.n else 0.0

    @property
    def helios_effect_acc(self) -> float:
        return self.helios_effect_correct / self.n if self.n else 0.0

    @property
    def baseline_segment_acc(self) -> float:
        return self.baseline_segment_correct / self.n if self.n else 0.0


def _helios_predict(segments: list) -> tuple[str, str]:
    res = decompose_change(segments)
    return res.segments[0].segment, res.dominant_effect


def score_benchmark(base: list) -> BenchmarkResult:
    """Build scenarios from a base segment table and score both methods."""
    scenarios = make_scenarios(base)
    r = BenchmarkResult(n=len(scenarios))
    for sc in scenarios:
        h_seg, h_eff = _helios_predict(sc.segments)
        b_seg = naive_largest_delta(sc.segments)
        seg_ok = (h_seg == sc.truth_segment)
        eff_ok = (h_eff == sc.truth_effect)
        base_ok = (b_seg == sc.truth_segment)
        r.helios_segment_correct += seg_ok
        r.helios_effect_correct += eff_ok
        r.baseline_segment_correct += base_ok
        r.rows.append({
            "scenario": sc.name,
            "truth_segment": sc.truth_segment,
            "truth_effect": sc.truth_effect,
            "helios_segment": h_seg,
            "helios_effect": h_eff,
            "helios_correct": bool(seg_ok and eff_ok),
            "baseline_segment": b_seg,
            "baseline_correct": bool(base_ok),
        })
    return r


def load_base_segments(client, project: str, dataset: str) -> list:
    """Aggregate fct_daily_funnel across all weeks into a (channel x device) base table."""
    from helios.diagnosis import load_weekly
    df = load_weekly(client, project, dataset)
    g = (df.groupby(["channel_group", "device_category"])
           .agg(num=("purchasing_sessions", "sum"), den=("sessions", "sum"))
           .reset_index())
    g = g[g["den"] > 0]
    return [{"segment": f"{row.channel_group} / {row.device_category}",
             "num": int(row.num), "den": int(row.den)} for row in g.itertuples()]


def base_segments_from_df(df) -> list:
    """Same as load_base_segments but from an already-loaded weekly DataFrame (dashboard)."""
    g = (df.groupby(["channel_group", "device_category"])
           .agg(num=("purchasing_sessions", "sum"), den=("sessions", "sum"))
           .reset_index())
    g = g[g["den"] > 0]
    return [{"segment": f"{row.channel_group} / {row.device_category}",
             "num": int(row.num), "den": int(row.den)} for row in g.itertuples()]
