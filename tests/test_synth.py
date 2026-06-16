"""Synthetic generator tests — the session-grain fct_funnel must be internally consistent
(monotonic funnel, revenue only on purchasers) and aggregate back to the daily funnel, so
the governed diagnosis reads the same numbers off either table. Offline.
Run: pytest tests/test_synth.py -v
"""
from datetime import date

from helios.synth.generator import generate_funnel_sessions, generate_daily_funnel

END = date(2021, 1, 31)
_ORDER = ["reached_view_item", "reached_add_to_cart", "reached_begin_checkout",
          "reached_add_shipping_info", "reached_add_payment_info", "reached_purchase"]


def test_funnel_flags_are_monotonic_and_revenue_only_on_purchasers():
    for r in generate_funnel_sessions(END, days=10, scale=0.5):
        seen_false = False
        for f in _ORDER:                      # flags must be non-increasing down the funnel
            if not r[f]:
                seen_false = True
            elif seen_false:
                raise AssertionError("non-monotonic funnel flags")
        if not r["reached_purchase"]:
            assert r["session_revenue"] == 0.0
        if r["session_revenue"] > 0:
            assert r["reached_purchase"] is True


def test_session_grain_aggregates_exactly_to_daily_at_full_scale():
    sessions = generate_funnel_sessions(END, days=10, scale=1.0)
    agg: dict = {}
    for r in sessions:
        k = (r["event_date"], r["channel_group"], r["device_category"])
        a = agg.setdefault(k, [0, 0])
        a[0] += 1                              # sessions = COUNT(DISTINCT session_key)
        a[1] += int(r["reached_purchase"])     # purchasing_sessions = COUNTIF(reached_purchase)

    daily: dict = {}
    for d in generate_daily_funnel(END, days=10):   # sum the two is_new rows per cell
        k = (d["event_date"], d["channel_group"], d["device_category"])
        a = daily.setdefault(k, [0, 0])
        a[0] += d["sessions"]
        a[1] += d["purchasing_sessions"]

    assert agg == daily   # exact reconciliation at scale 1.0
