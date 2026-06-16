"""Critic tests — the verify-then-trust firewall must SHIP clean findings and REFUTE /
REVISE the ones that fail an adversarial check. Pure-Python; no BigQuery.
Run: pytest tests/test_critic.py -v
"""
from types import SimpleNamespace

from helios.critic import critique


def _diag(**over):
    """A clean, ship-worthy rate-dominant diagnosis; override fields to break a check."""
    base = dict(
        delta=-0.012, mix=-0.001, rate=-0.010, interaction=-0.001, dominant="rate",
        conv_t0=0.030, conv_t1=0.018, p_value=0.001, significant=True,
        sessions_t1=100_000, aov=60.0, revenue_at_risk=-60_000.0,
        drivers=[{"segment": "Paid Search / mobile"}],
        funnel_t0={"Sessions": 1000, "Cart": 400, "Purchase": 30},
        funnel_t1={"Sessions": 1000, "Cart": 380, "Purchase": 18},
    )
    base.update(over)
    return SimpleNamespace(**base)


def test_clean_rate_finding_ships():
    r = critique(_diag())
    assert r.verdict == "SHIP"
    assert all(c.status == "PASS" for c in r.checks)


def test_non_reconciling_decomposition_is_refuted():
    # components no longer sum to delta -> G4 reconcile failure -> hard refute
    r = critique(_diag(mix=0.05, rate=0.05, interaction=0.05))
    assert r.verdict == "REFUTE"
    assert any(c.name == "reconcile" and c.status == "FAIL" for c in r.checks)


def test_mix_dominant_warns_against_fixing_the_funnel():
    r = critique(_diag(dominant="mix", mix=-0.010, rate=-0.001, interaction=-0.001))
    assert r.verdict == "REVISE"
    framing = next(c for c in r.checks if c.name == "mix-vs-rate framing")
    assert framing.status == "WARN"
    assert "acquisition" in framing.detail.lower()


def test_non_significant_move_warns():
    r = critique(_diag(significant=False, p_value=0.4))
    assert r.verdict == "REVISE"
    assert any(c.name == "significance" and c.status == "WARN" for c in r.checks)


def test_non_monotonic_funnel_is_refuted():
    # Purchase > Cart is impossible -> data-quality refute
    r = critique(_diag(funnel_t1={"Sessions": 1000, "Cart": 380, "Purchase": 500}))
    assert r.verdict == "REFUTE"
    assert any(c.name == "data quality" and c.status == "FAIL" for c in r.checks)


def test_implausible_dollars_are_refuted():
    # revenue-at-risk far exceeds sessions * aov ceiling
    r = critique(_diag(revenue_at_risk=-999_000_000.0))
    assert r.verdict == "REFUTE"
    assert any(c.name == "dollar sanity" and c.status == "FAIL" for c in r.checks)
