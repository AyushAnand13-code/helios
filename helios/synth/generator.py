"""Generate a realistic, recent-dated fct_daily_funnel (synthetic 'live' data).

Shapes mimic GA4 e-commerce: 10 channel groups x 3 devices x new/returning, weekly
seasonality + mild growth + daily noise, a monotonic funnel, and a planted INCIDENT in
the most recent week so the diagnosis surfaces a fresh, dated, actionable finding.

The incident is a mobile checkout regression: in-segment conversion on `mobile` drops
~38% across channels over the last 7 days. Because mobile is ~58% of traffic this moves
the AGGREGATE weekly conversion by a material, statistically-significant amount — a
genuine 'rate' anomaly concentrated in the mobile cells, not a tiny segment blip. That is
what makes the autonomous run alert on a NEW finding rather than shrug it off as noise.
Deterministic per (end_date, seed) so a given day's run is reproducible.
"""
from __future__ import annotations
import hashlib
import math
import random
from datetime import date, timedelta

# (channel_group, traffic weight, base session->purchase conversion)
CHANNELS = [
    ("Organic Search", 1.00, 0.018), ("Direct", 0.85, 0.016),
    ("Paid Search", 0.55, 0.022), ("Referral", 0.35, 0.030),
    ("Email", 0.18, 0.034), ("Organic Social", 0.45, 0.011),
    ("Paid Social", 0.40, 0.013), ("Display", 0.30, 0.008),
    ("Affiliates", 0.12, 0.021), ("Other", 0.15, 0.009),
]
_CH_W = sum(c[1] for c in CHANNELS)
# (device, traffic share, conversion multiplier)
DEVICES = [("mobile", 0.58, 0.85), ("desktop", 0.36, 1.30), ("tablet", 0.06, 0.95)]

# planted recent incident: a mobile checkout regression (in-segment conversion drop on
# `mobile` across all channels) over the last N days. Mobile's large traffic share makes
# this aggregate-material and significant -> the autonomous run flags a NEW finding.
ANOM_DEVICE, ANOM_DAYS, ANOM_FACTOR = "mobile", 7, 0.62   # ~38% mobile conversion drop

_DAILY_SESSIONS = 14000   # total sessions/day baseline


def _key(*parts) -> str:
    return hashlib.md5("|".join(map(str, parts)).encode()).hexdigest()


def generate_daily_funnel(end_date: date, days: int = 90, seed: int | None = None) -> list[dict]:
    """Return fct_daily_funnel rows for [end_date-days+1 .. end_date]."""
    rng = random.Random(seed if seed is not None else end_date.toordinal())
    start = end_date - timedelta(days=days - 1)
    anom_start = end_date - timedelta(days=ANOM_DAYS - 1)
    rows: list[dict] = []

    for i in range(days):
        d = start + timedelta(days=i)
        season = 1.0 + 0.12 * math.sin((i / 7.0) * 2 * math.pi)   # weekly wave
        weekend = 0.88 if d.weekday() >= 5 else 1.0
        trend = 1.0 + 0.0010 * i                                  # mild growth
        day_factor = season * weekend * trend * (1.0 + rng.uniform(-0.06, 0.06))

        for ch_name, ch_w, ch_conv in CHANNELS:
            for dev_name, dev_share, dev_mult in DEVICES:
                for is_new in (True, False):
                    new_share = 0.62 if is_new else 0.38
                    sessions = (_DAILY_SESSIONS * (ch_w / _CH_W) * dev_share * new_share
                                * day_factor * (1.0 + rng.uniform(-0.10, 0.10)))
                    sessions = int(round(sessions))
                    if sessions <= 0:
                        continue

                    # monotonic funnel built downward; final purchase rate carries the
                    # channel/device conversion + the planted anomaly.
                    view = int(round(sessions * rng.uniform(0.55, 0.72)))
                    cart = int(round(view * rng.uniform(0.36, 0.50)))
                    checkout = int(round(cart * rng.uniform(0.55, 0.75)))
                    shipping = int(round(checkout * rng.uniform(0.72, 0.86)))
                    payment = int(round(shipping * rng.uniform(0.80, 0.92)))

                    conv_factor = dev_mult * (0.8 if is_new else 1.25)
                    if (dev_name == ANOM_DEVICE and d >= anom_start):
                        conv_factor *= ANOM_FACTOR    # mobile checkout regression, last 7 days
                    # implied final-step rate to hit ~ ch_conv * conv_factor overall
                    target_purch = sessions * min(0.45, max(0.0006, ch_conv * conv_factor
                                                            * (1.0 + rng.uniform(-0.08, 0.08))))
                    purchase = int(round(min(payment, target_purch)))

                    # rounding safety -> strict monotonicity
                    view = min(view, sessions); cart = min(cart, view)
                    checkout = min(checkout, cart); shipping = min(shipping, checkout)
                    payment = min(payment, shipping); purchase = max(0, min(purchase, payment))

                    aov = rng.uniform(48, 82)
                    rows.append({
                        "daily_funnel_key": _key(d, ch_name, dev_name, "US", is_new),
                        "event_date": d.isoformat(),
                        "channel_group": ch_name,
                        "device_category": dev_name,
                        "country": "United States",
                        "is_new_user": bool(is_new),
                        "sessions": sessions,
                        "view_item_sessions": view,
                        "add_to_cart_sessions": cart,
                        "begin_checkout_sessions": checkout,
                        "add_shipping_info_sessions": shipping,
                        "add_payment_info_sessions": payment,
                        "purchasing_sessions": purchase,
                        "transactions": purchase,
                        "revenue": round(purchase * aov, 2),
                    })
    return rows
