"""Reusable Helios diagnosis logic — shared by diagnose.py (CLI) and app.py (dashboard).

Pulls weekly funnel data through the GOVERNED path (semantic-mcp composes the SQL from
the registry; warehouse dry-run-checks and runs it) and turns a week-over-week conversion
move into a structured diagnosis (mix vs rate, significance, dollar impact, drivers).
No SQL is hand-authored here (G1); the cost is checked before running (G3).
"""
from __future__ import annotations
from dataclasses import dataclass

from .stats import decompose_change, two_proportion_ztest
from .semantic import SemanticLayer
from .warehouse import Warehouse

# The macro funnel, in order. Each entry is a governed metric name in the registry.
FUNNEL_STEPS = [
    ("sessions", "Sessions"),
    ("view_item_sessions", "View Item"),
    ("add_to_cart_sessions", "Add to Cart"),
    ("begin_checkout_sessions", "Begin Checkout"),
    ("add_shipping_info_sessions", "Add Shipping"),
    ("add_payment_info_sessions", "Add Payment"),
    ("purchasing_sessions", "Purchase"),
]

_METRICS = [c for c, _ in FUNNEL_STEPS] + ["revenue"]
_SUM_COLS = list(_METRICS)
_DIMENSIONS = ["week", "channel_group", "device_category"]


def build_weekly_sql(project: str | None, dataset: str, layer: SemanticLayer | None = None) -> str:
    """Compose the governed weekly funnel query from the registry (never hand-authored)."""
    layer = layer or SemanticLayer()
    return layer.build_query(_METRICS, _DIMENSIONS, project=project, dataset=dataset)


def load_weekly(client, project: str, dataset: str, *,
                layer: SemanticLayer | None = None, warehouse: Warehouse | None = None):
    """Return a pandas DataFrame at (week x channel_group x device_category) grain.

    The SQL is composed by the semantic layer (G1) and executed through the warehouse,
    which dry-run cost-checks it first (G3). `layer`/`warehouse` are injectable for tests.
    """
    import pandas as pd
    sql = build_weekly_sql(project, dataset, layer)
    wh = warehouse or Warehouse(client, project=project)
    rows = wh.run_query(sql)
    df = pd.DataFrame(rows)
    df["week"] = df["week"].astype(str)
    for c in _SUM_COLS:
        df[c] = df[c].fillna(0)
    return df


def weeks_in(df) -> list[str]:
    return sorted(df["week"].unique())


def biggest_move(df) -> tuple[str, str]:
    """Adjacent week-pair with the largest absolute change in overall conversion."""
    g = df.groupby("week").agg(sessions=("sessions", "sum"),
                               purch=("purchasing_sessions", "sum"))
    g["conv"] = g["purch"] / g["sessions"].where(g["sessions"] != 0)
    ws = list(g.index)
    best = None
    for a, b in zip(ws, ws[1:]):
        d = abs((g.loc[b, "conv"] or 0) - (g.loc[a, "conv"] or 0))
        if best is None or d > best[0]:
            best = (d, a, b)
    if best is None:
        return ws[0], ws[-1] if len(ws) > 1 else ws[0]
    return best[1], best[2]


@dataclass
class Diagnosis:
    w0: str
    w1: str
    conv_t0: float
    conv_t1: float
    delta: float
    mix: float
    rate: float
    interaction: float
    dominant: str
    p_value: float
    significant: bool
    sessions_t1: int
    aov: float
    revenue_at_risk: float
    drivers: list          # list[dict]
    funnel_t0: dict
    funnel_t1: dict


def run_diagnosis(df, w0: str, w1: str) -> Diagnosis:
    """Decompose the conversion change between two weeks into mix/rate + dollars."""
    sub = df[df["week"].isin([w0, w1])]

    keyed: dict = {}
    for r in sub.itertuples(index=False):
        k = (r.channel_group, r.device_category)
        s = keyed.setdefault(k, {"num_t0": 0, "den_t0": 0, "num_t1": 0, "den_t1": 0})
        if r.week == w0:
            s["num_t0"] += r.purchasing_sessions
            s["den_t0"] += r.sessions
        else:
            s["num_t1"] += r.purchasing_sessions
            s["den_t1"] += r.sessions

    segs = [{"segment": f"{ch} / {dev}", **v} for (ch, dev), v in keyed.items()]
    res = decompose_change(segs)

    t0, t1 = df[df.week == w0], df[df.week == w1]
    sess_t0, sess_t1 = int(t0.sessions.sum()), int(t1.sessions.sum())
    pur_t0, pur_t1 = int(t0.purchasing_sessions.sum()), int(t1.purchasing_sessions.sum())
    rev_t1 = float(t1.revenue.sum())

    sig = two_proportion_ztest(pur_t0, sess_t0, pur_t1, sess_t1)
    aov = rev_t1 / pur_t1 if pur_t1 else 0.0
    revenue_at_risk = res.rate_effect * sess_t1 * aov

    drivers = [{
        "segment": c.segment,
        "total_pts": c.total * 100,
        "mix_pts": c.mix * 100,
        "rate_pts": c.rate * 100,
        "conv_t0_pct": c.r_t0 * 100,
        "conv_t1_pct": c.r_t1 * 100,
    } for c in res.segments[:8]]

    funnel_t0 = {lbl: int(t0[col].sum()) for col, lbl in FUNNEL_STEPS}
    funnel_t1 = {lbl: int(t1[col].sum()) for col, lbl in FUNNEL_STEPS}

    return Diagnosis(
        w0=w0, w1=w1,
        conv_t0=res.r_t0, conv_t1=res.r_t1, delta=res.delta,
        mix=res.mix_effect, rate=res.rate_effect, interaction=res.interaction,
        dominant=res.dominant_effect,
        p_value=sig.p_value, significant=sig.significant,
        sessions_t1=sess_t1, aov=aov, revenue_at_risk=revenue_at_risk,
        drivers=drivers, funnel_t0=funnel_t0, funnel_t1=funnel_t1,
    )
