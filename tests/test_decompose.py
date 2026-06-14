"""Golden-value tests for the decomposition engine — the keystone math.

Run: pytest tests/test_decompose.py -v
These are pure-Python (no BigQuery) and pin the exact mix/rate/interaction algebra
the diagnosis depends on.
"""
import math
from helios.stats import decompose_change, two_proportion_ztest


def approx(a, b, tol=1e-9):
    return math.isclose(a, b, abs_tol=tol)


def test_pure_mix_shift_golden():
    """Composition shifts toward the lower-converting segment; rates UNCHANGED.

    Matches the project's stated golden: mix=-0.0018, rate=0, interaction=0.
    A: rate 0.05, weight 0.50 -> 0.44 ;  B: rate 0.02, weight 0.50 -> 0.56.
    delta = (0.44*0.05 + 0.56*0.02) - (0.50*0.05 + 0.50*0.02) = 0.0332 - 0.0350 = -0.0018
    """
    segs = [
        {"segment": "A", "num_t0": 25, "den_t0": 500, "num_t1": 22.0, "den_t1": 440},
        {"segment": "B", "num_t0": 10, "den_t0": 500, "num_t1": 11.2, "den_t1": 560},
    ]
    r = decompose_change(segs)
    assert approx(r.mix_effect, -0.0018)
    assert approx(r.rate_effect, 0.0)
    assert approx(r.interaction, 0.0)
    assert approx(r.delta, -0.0018)
    assert r.dominant_effect == "mix"
    assert r.check_additive()


def test_pure_rate_change():
    """Weights identical; only in-segment rate moves -> all effect is 'rate'."""
    segs = [
        {"segment": "A", "num_t0": 50, "den_t0": 1000, "num_t1": 40, "den_t1": 1000},
        {"segment": "B", "num_t0": 20, "den_t0": 1000, "num_t1": 20, "den_t1": 1000},
    ]
    r = decompose_change(segs)
    assert approx(r.mix_effect, 0.0)
    # rate A drops 0.05 -> 0.04 at weight 0.5 => -0.005
    assert approx(r.rate_effect, -0.005)
    assert approx(r.interaction, 0.0)
    assert approx(r.delta, -0.005)
    assert r.dominant_effect == "rate"
    assert r.check_additive()


def test_additivity_always_holds():
    """For arbitrary inputs, mix + rate + interaction == delta exactly."""
    segs = [
        {"segment": "X", "num_t0": 13, "den_t0": 211, "num_t1": 31, "den_t1": 509},
        {"segment": "Y", "num_t0": 7, "den_t0": 88, "num_t1": 2, "den_t1": 140},
        {"segment": "Z", "num_t0": 41, "den_t0": 333, "num_t1": 39, "den_t1": 301},
    ]
    r = decompose_change(segs)
    assert r.check_additive()
    assert approx(r.mix_effect + r.rate_effect + r.interaction, r.delta)


def test_two_proportion_significance():
    """A large, clear rate drop is significant; a tiny one is not."""
    big = two_proportion_ztest(num_a=500, den_a=10000, num_b=300, den_b=10000)
    assert big.significant and big.p_value < 0.001

    tiny = two_proportion_ztest(num_a=500, den_a=10000, num_b=498, den_b=10000)
    assert not tiny.significant
