#!/usr/bin/env python
"""eval_run.py — Helios v1 honest benchmark.

Injects known funnel anomalies into the real segment mix and scores whether the
mix-vs-rate decomposition recovers the true cause, vs a naive 'largest-segment-delta'
baseline. Controlled-attribution accuracy (not causal): we know the injected cause.

Usage:  python eval_run.py
        python eval_run.py --project helios-mvp --dataset helios_dev_marts
"""
from __future__ import annotations
import argparse
import os
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=os.environ.get("HELIOS_PROJECT", "helios-mvp"))
    ap.add_argument("--dataset", default=os.environ.get("HELIOS_MARTS_DATASET", "helios_dev_marts"))
    args = ap.parse_args()

    from google.cloud import bigquery
    from helios.eval.runner import load_base_segments, score_benchmark

    print(f"Loading base segments from {args.project}.{args.dataset} …")
    client = bigquery.Client(project=args.project)
    base = load_base_segments(client, args.project, args.dataset)
    print(f"{len(base)} segments. Injecting scenarios + scoring …\n")

    r = score_benchmark(base)

    print(f"{'scenario':34} {'truth':6} | Helios            | naive baseline")
    print("-" * 86)
    for row in r.rows:
        h = "OK  " if row["helios_correct"] else "MISS"
        b = "OK  " if row["baseline_correct"] else "MISS"
        print(f"{row['scenario']:34} {row['truth_effect']:6} | "
              f"{h} ({row['helios_effect']:4}) | {b}")
    print("-" * 86)
    print(f"\nHELIOS  — segment: {r.helios_segment_correct}/{r.n} "
          f"({r.helios_segment_acc*100:.0f}%)   "
          f"segment+effect: {r.helios_effect_correct}/{r.n} ({r.helios_effect_acc*100:.0f}%)")
    print(f"NAIVE   — segment: {r.baseline_segment_correct}/{r.n} "
          f"({r.baseline_segment_acc*100:.0f}%)")
    print("\nThe baseline is blind to mix-shifts (no segment's rate moves), which is exactly")
    print("where the governed mix-vs-rate decomposition earns its keep. Controlled")
    print("attribution accuracy — it proves we recover the injected cause, not causation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
