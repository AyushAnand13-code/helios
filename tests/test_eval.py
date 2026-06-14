"""Eval benchmark tests — Helios must recover the injected cause and beat the naive
baseline, especially on mix-shifts (which the baseline is structurally blind to).
Pure-Python; no BigQuery. Run: pytest tests/test_eval.py -v
"""
from helios.eval.runner import score_benchmark
from helios.eval.injector import inject_rate, inject_mix
from helios.eval.baselines import naive_largest_delta, NO_SIGNAL
from helios.stats import decompose_change

BASE = [
    {"segment": "Direct / desktop", "num": 400, "den": 10000},
    {"segment": "Direct / mobile", "num": 200, "den": 15000},
    {"segment": "Organic / desktop", "num": 300, "den": 8000},
    {"segment": "Organic / mobile", "num": 150, "den": 12000},
    {"segment": "Referral / desktop", "num": 250, "den": 5000},
    {"segment": "Paid / mobile", "num": 50, "den": 3000},
]


def test_helios_perfect_on_injected_causes():
    r = score_benchmark(BASE)
    # Helios recovers the right segment AND effect type on every injected scenario.
    assert r.helios_segment_correct == r.n
    assert r.helios_effect_correct == r.n


def test_helios_beats_naive_baseline():
    r = score_benchmark(BASE)
    assert r.helios_segment_acc > r.baseline_segment_acc


def test_baseline_blind_to_mix_shift():
    # A pure mix-shift moves no segment's rate -> the naive baseline reports no signal.
    sc = inject_mix(BASE, "Direct / mobile", 2.0)
    assert naive_largest_delta(sc.segments) == NO_SIGNAL
    # ...but the decomposition attributes it to the shifted segment as a MIX effect.
    res = decompose_change(sc.segments)
    assert res.dominant_effect == "mix"
    assert res.segments[0].segment == "Direct / mobile"


def test_rate_injection_is_rate_dominant():
    sc = inject_rate(BASE, "Direct / desktop", 0.5)
    res = decompose_change(sc.segments)
    assert res.dominant_effect == "rate"
    assert res.segments[0].segment == "Direct / desktop"
