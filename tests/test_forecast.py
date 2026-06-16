"""Forecast / anomaly-detection tests — flag a real deviation, ignore normal noise, and
the forecast-based week selector. Pure-Python. Run: pytest tests/test_forecast.py -v
"""
import pytest

from helios.stats import detect_anomaly, forecast_next

STABLE = [0.020, 0.021, 0.019, 0.020, 0.0205, 0.0195, 0.020, 0.021, 0.0198]


def test_stable_series_has_no_anomalies():
    assert [p.index for p in detect_anomaly(STABLE) if p.is_anomaly] == []


def test_planted_drop_is_flagged():
    pts = detect_anomaly(STABLE + [0.012])      # a real last-week conversion drop
    flagged = [p for p in pts if p.is_anomaly]
    assert len(flagged) == 1
    assert flagged[0].index == len(STABLE)
    assert flagged[0].z < -2.5                  # a downward anomaly


def test_low_volume_normal_rate_is_not_flagged():
    # The whole point: a normal RATE is not an anomaly regardless of volume.
    assert not any(p.is_anomaly for p in detect_anomaly(STABLE + [0.0202]))


def test_forecast_interval_brackets_a_stable_next_point():
    fc = forecast_next(STABLE)
    assert fc["lower"] < fc["forecast"] < fc["upper"]
    assert fc["lower"] <= 0.0202 <= fc["upper"]   # a normal next week sits inside the PI


def test_forecast_needs_data():
    with pytest.raises(ValueError):
        forecast_next([])


def test_most_anomalous_move_picks_the_anomaly_week():
    pd = pytest.importorskip("pandas")
    # 6 normal weeks then a sharp drop in the last week; biggest raw delta is also the last
    # pair here, but the selector must pick it via the forecast, not the raw delta.
    weeks = [f"2021-01-{d:02d}" for d in (4, 11, 18, 25)] + ["2021-02-01", "2021-02-08"]
    convs = [0.020, 0.0205, 0.0198, 0.0202, 0.0200, 0.0120]
    rows = []
    for wk, cv in zip(weeks, convs):
        sess = 50000
        rows.append({"week": wk, "channel_group": "Direct", "device_category": "desktop",
                     "sessions": sess, "purchasing_sessions": int(round(sess * cv))})
    from helios.diagnosis import most_anomalous_move
    w0, w1 = most_anomalous_move(pd.DataFrame(rows))
    assert w1 == "2021-02-08" and w0 == "2021-02-01"
