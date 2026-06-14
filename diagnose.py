#!/usr/bin/env python
"""diagnose.py — Helios MVP: governed mix-vs-rate diagnosis of the GA4 funnel. No LLM.

Finds the biggest week-over-week move in session conversion, decomposes it into
mix-shift vs rate-change across (channel_group x device_category), tests significance,
prices it in dollars of revenue-at-risk, and prints a templated Decision Brief.

ALL numbers come from the governed marts (fct_daily_funnel) and the deterministic
stats engine (helios.stats) — nothing is computed in prose.

PREREQUISITES (your one-time setup): a successful `dbt build` so the marts exist,
and `gcloud auth application-default login`.

Usage:
    python diagnose.py                 # uses env / gcloud defaults
    python diagnose.py --project my-proj --dataset helios_dev_marts

Config (CLI flag overrides env var):
    --project   HELIOS_PROJECT          GCP project id (else gcloud ADC default)
    --dataset   HELIOS_MARTS_DATASET    marts dataset  (default: helios_dev_marts)
"""
from __future__ import annotations
import argparse
import os
import sys

from helios.stats import decompose_change, two_proportion_ztest


def get_client(project: str | None):
    try:
        from google.cloud import bigquery
    except ImportError:
        sys.exit("ERROR: google-cloud-bigquery not installed. Run: pip install -r requirements.txt")
    return bigquery.Client(project=project) if project else bigquery.Client()


def fetch_week_segments(client, project: str, dataset: str):
    """Pull weekly x (channel_group, device_category) funnel counts from fct_daily_funnel."""
    table = f"`{project}.{dataset}.fct_daily_funnel`" if project else f"`{dataset}.fct_daily_funnel`"
    sql = f"""
        SELECT
            DATE_TRUNC(event_date, WEEK(MONDAY)) AS week,
            channel_group,
            device_category,
            SUM(sessions)            AS sessions,
            SUM(purchasing_sessions) AS purchasers,
            SUM(revenue)             AS revenue
        FROM {table}
        GROUP BY 1, 2, 3
        ORDER BY 1
    """
    rows = list(client.query(sql).result())
    if not rows:
        sys.exit(f"ERROR: {table} returned no rows. Did `dbt build` succeed?")
    return rows


def pick_biggest_move(rows):
    """Return (week_t0, week_t1) of the adjacent week-pair with the largest |delta conv|."""
    weeks: dict = {}
    for r in rows:
        w = r["week"]
        agg = weeks.setdefault(w, {"sessions": 0, "purchasers": 0})
        agg["sessions"] += r["sessions"] or 0
        agg["purchasers"] += r["purchasers"] or 0
    ordered = sorted(weeks)
    best = None
    for a, b in zip(ordered, ordered[1:]):
        ca = weeks[a]["purchasers"] / weeks[a]["sessions"] if weeks[a]["sessions"] else 0
        cb = weeks[b]["purchasers"] / weeks[b]["sessions"] if weeks[b]["sessions"] else 0
        d = abs(cb - ca)
        if best is None or d > best[0]:
            best = (d, a, b)
    if best is None:
        sys.exit("ERROR: need at least two weeks of data to compare.")
    return best[1], best[2]


def build_segments(rows, w0, w1):
    """Assemble decompose_change input over the union of segments in the two weeks."""
    keyed: dict = {}
    for r in rows:
        if r["week"] not in (w0, w1):
            continue
        key = (r["channel_group"], r["device_category"])
        slot = keyed.setdefault(key, {"num_t0": 0, "den_t0": 0, "num_t1": 0, "den_t1": 0,
                                      "rev_t1": 0.0})
        if r["week"] == w0:
            slot["num_t0"] += r["purchasers"] or 0
            slot["den_t0"] += r["sessions"] or 0
        else:
            slot["num_t1"] += r["purchasers"] or 0
            slot["den_t1"] += r["sessions"] or 0
            slot["rev_t1"] += float(r["revenue"] or 0.0)
    segs = []
    rev_t1 = 0.0
    for (ch, dev), v in keyed.items():
        segs.append({"segment": f"{ch} / {dev}", **{k: v[k] for k in
                     ("num_t0", "den_t0", "num_t1", "den_t1")}})
        rev_t1 += v["rev_t1"]
    return segs, rev_t1


def money(x: float) -> str:
    return f"${x:,.0f}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=os.environ.get("HELIOS_PROJECT"))
    ap.add_argument("--dataset", default=os.environ.get("HELIOS_MARTS_DATASET", "helios_dev_marts"))
    args = ap.parse_args()

    client = get_client(args.project)
    project = args.project or client.project
    rows = fetch_week_segments(client, project, args.dataset)

    w0, w1 = pick_biggest_move(rows)
    segs, rev_t1 = build_segments(rows, w0, w1)
    result = decompose_change(segs)

    sess_t0 = sum(s["den_t0"] for s in segs)
    sess_t1 = sum(s["den_t1"] for s in segs)
    purch_t0 = sum(s["num_t0"] for s in segs)
    purch_t1 = sum(s["num_t1"] for s in segs)
    sig = two_proportion_ztest(purch_t0, sess_t0, purch_t1, sess_t1)

    aov = (rev_t1 / purch_t1) if purch_t1 else 0.0
    # Dollars of revenue-at-risk attributable to the in-segment RATE change:
    rev_at_risk = result.rate_effect * sess_t1 * aov

    direction = "DROP" if result.delta < 0 else "RISE"
    print("=" * 70)
    print(f"  HELIOS DECISION BRIEF — session conversion {direction}")
    print(f"  {w0}  ->  {w1}   (week over week)")
    print("=" * 70)
    print(f"\nHEADLINE")
    print(f"  Session conversion moved {result.r_t0*100:.2f}%  ->  {result.r_t1*100:.2f}%  "
          f"({result.delta*100:+.2f} pts).")
    print(f"  Statistical significance: p = {sig.p_value:.2e} "
          f"({'SIGNIFICANT' if sig.significant else 'not significant'} at alpha=0.05).")

    print(f"\nWHY IT MOVED  (mix-shift vs rate-change)")
    print(f"  mix effect   {result.mix_effect*100:+.3f} pts   (traffic composition changed)")
    print(f"  rate effect  {result.rate_effect*100:+.3f} pts   (in-segment behaviour changed)")
    print(f"  interaction  {result.interaction*100:+.3f} pts   (both moved together)")
    print(f"  -> DOMINANT EFFECT: {result.dominant_effect.upper()}.")
    if result.dominant_effect == "mix":
        print("     Composition artifact: your traffic shifted between segments that convert")
        print("     differently. The funnel itself may be fine — do NOT 'fix checkout' blindly.")
    else:
        print("     Real behaviour change inside segments — worth a funnel/UX investigation.")

    print(f"\nTOP DRIVER SEGMENTS  (largest contribution to the move)")
    for c in result.segments[:3]:
        print(f"  {c.segment:<34} total {c.total*100:+.3f} pts  "
              f"(mix {c.mix*100:+.3f}, rate {c.rate*100:+.3f})  "
              f"conv {c.r_t0*100:.2f}%->{c.r_t1*100:.2f}%")

    print(f"\nDOLLAR IMPACT")
    print(f"  AOV (week {w1}): {money(aov)}   |   sessions: {sess_t1:,}")
    print(f"  Revenue-at-risk from the RATE change: {money(rev_at_risk)} "
          f"({'lost' if rev_at_risk < 0 else 'gained'} this week).")

    print(f"\nRECOMMENDED ACTION")
    if not sig.significant:
        print("  Move is not statistically significant — monitor, do not act yet.")
    elif result.dominant_effect == "mix":
        print("  Investigate the traffic-mix shift (acquisition/channel changes), not the funnel.")
    else:
        top = result.segments[0]
        print(f"  Drill the rate change in '{top.segment}' — run a funnel-step diagnosis and a")
        print(f"  targeted experiment there; it carries the largest in-segment behaviour move.")
    print("\n" + "=" * 70)
    print("All figures are governed mart + deterministic-stats outputs (no LLM, no hand SQL).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
