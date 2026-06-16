"""Synthetic 'live' funnel feed.

Generates realistic, recent-dated fct_daily_funnel rows so the demo always shows current
weeks (the public GA4 sample is frozen at 2020-2021). CLEARLY SYNTHETIC — it mimics GA4
funnel shapes (channels, devices, weekly seasonality, a planted recent anomaly) so the
governed diagnosis has something real to find. Powers the autonomous scheduled run.
"""
from .generator import generate_daily_funnel  # noqa: F401
