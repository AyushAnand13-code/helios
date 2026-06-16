#!/usr/bin/env python
"""eval_labeled.py — Helios offline 50-scenario benchmark + CI gate.

Runs every labeled scenario in eval/scenarios/scenarios.yaml through the real
mix-vs-rate engine plus the materiality / seasonality / data-quality guards, scores the
prediction against the ground-truth labels, prints a per-bucket report, writes a JSON
result, and (with --gate) exits non-zero if accuracy regresses or any segment is
hallucinated. No BigQuery — pure Python.

Usage:
    python eval_labeled.py                 # report only
    python eval_labeled.py --gate          # also enforce eval/gates.yaml (CI)
    python eval_labeled.py --json out.json # write machine-readable result
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from helios.eval.labeled import load_scenarios, score_labeled, DEFAULT_SCENARIOS

GATES = Path(__file__).resolve().parent / "eval" / "gates.yaml"
RESULTS_DIR = Path(__file__).resolve().parent / "eval" / "benchmark_results"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios", default=str(DEFAULT_SCENARIOS))
    ap.add_argument("--gate", action="store_true", help="enforce eval/gates.yaml; nonzero exit on regression")
    ap.add_argument("--json", default=None, help="write the JSON result to this path")
    args = ap.parse_args()

    scenarios = load_scenarios(args.scenarios)
    r = score_labeled(scenarios)

    print(f"{'id':5} {'bucket':22} {'truth':12} {'pred':12} {'seg?':5} result")
    print("-" * 78)
    for row in r.rows:
        seg = "ok" if (row.truth_segment is None or row.segment_hit) else "MISS"
        mark = "OK  " if row.correct else "MISS"
        print(f"{row.sid:5} {row.bucket:22} {row.truth_effect:12} "
              f"{row.pred.effect:12} {seg:5} {mark}")
    print("-" * 78)

    print("\nPer bucket:")
    for bucket, (c, n) in sorted(r.by_bucket().items()):
        print(f"  {bucket:22} {c}/{n} ({c/n*100:.0f}%)")

    print(f"\nOVERALL root-cause accuracy : {r.correct}/{r.n} ({r.accuracy*100:.1f}%)")
    print(f"Top-1 segment accuracy      : {r.segment_accuracy*100:.1f}% "
          f"(over scenarios with a root-cause segment)")
    print(f"Hallucinated segments       : {len(r.hallucinations)}  "
          f"{'(' + ', '.join(r.hallucinations) + ')' if r.hallucinations else '(none — fully governed)'}")

    result = {
        "n": r.n,
        "accuracy": round(r.accuracy, 4),
        "segment_accuracy": round(r.segment_accuracy, 4),
        "hallucinations": r.hallucinations,
        "by_bucket": {k: {"correct": c, "n": n} for k, (c, n) in r.by_bucket().items()},
        "rows": [{"id": x.sid, "bucket": x.bucket, "truth_effect": x.truth_effect,
                  "pred_effect": x.pred.effect, "segment_hit": x.segment_hit,
                  "correct": x.correct} for x in r.rows],
    }
    out_path = Path(args.json) if args.json else (RESULTS_DIR / "labeled_latest.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")

    if args.gate:
        return _enforce_gate(result)
    return 0


def _enforce_gate(result: dict) -> int:
    import yaml
    if not GATES.exists():
        print(f"ERROR: gate file {GATES} not found.", file=sys.stderr)
        return 2
    gates = yaml.safe_load(GATES.read_text(encoding="utf-8"))
    min_acc = float(gates.get("min_accuracy", 0.85))
    min_seg = float(gates.get("min_segment_accuracy", 0.85))
    max_hall = int(gates.get("max_hallucinations", 0))

    failures = []
    if result["accuracy"] < min_acc:
        failures.append(f"accuracy {result['accuracy']*100:.1f}% < gate {min_acc*100:.0f}%")
    if result["segment_accuracy"] < min_seg:
        failures.append(f"segment accuracy {result['segment_accuracy']*100:.1f}% < gate {min_seg*100:.0f}%")
    if len(result["hallucinations"]) > max_hall:
        failures.append(f"{len(result['hallucinations'])} hallucinations > gate {max_hall}")

    print("\n" + "=" * 40)
    if failures:
        print("GATE FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"GATE PASSED (accuracy {result['accuracy']*100:.1f}% >= {min_acc*100:.0f}%, "
          f"0 hallucinations).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
