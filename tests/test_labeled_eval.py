"""Labeled 50-scenario benchmark tests — the CI regression firewall in unit-test form.
The offline harness must clear the eval/gates.yaml floors and never hallucinate a segment.
Pure-Python; no BigQuery. Run: pytest tests/test_labeled_eval.py -v
"""
from pathlib import Path

import yaml

from helios.eval.labeled import load_scenarios, score_labeled

GATES = yaml.safe_load((Path(__file__).resolve().parents[1] / "eval" / "gates.yaml")
                       .read_text(encoding="utf-8"))


def _result():
    return score_labeled(load_scenarios())


def test_all_fifty_scenarios_present():
    assert _result().n == 50


def test_meets_accuracy_gate():
    r = _result()
    assert r.accuracy >= GATES["min_accuracy"], f"accuracy {r.accuracy:.3f} below gate"


def test_meets_segment_accuracy_gate():
    r = _result()
    assert r.segment_accuracy >= GATES["min_segment_accuracy"]


def test_no_hallucinated_segments():
    # Governed: every predicted segment must be a real synthesized label.
    assert _result().hallucinations == []


def test_every_bucket_covered_and_scored():
    by_bucket = _result().by_bucket()
    expected = {"single_segment_rate", "single_segment_mix", "multi_segment_rate",
                "multi_segment_mixed", "seasonality_decoy", "no_anomaly_control",
                "data_quality"}
    assert set(by_bucket) == expected
    # No bucket may be a total wipe-out (would mean a guard/engine regression).
    for bucket, (correct, n) in by_bucket.items():
        assert correct > 0, f"bucket {bucket} scored 0/{n}"


def test_deterministic():
    # Same scenarios in -> identical accuracy (seeded synthesis, no randomness leak).
    assert score_labeled(load_scenarios()).accuracy == score_labeled(load_scenarios()).accuracy
