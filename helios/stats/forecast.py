"""Forecast-based anomaly detection — deterministic, dependency-light (stdlib + scipy).

The naive "biggest week-over-week move" picks whatever pair has the largest raw delta —
often a partial boundary week with normal *rates* but low volume. Instead we forecast each
point from its recent history (a short rolling level) and flag points whose actual value
falls far outside the residual-based prediction interval. Because it runs on the
conversion-RATE series, a low-volume week with a normal rate is NOT flagged — exactly the
artifact we want to ignore.

No prophet/statsmodels dependency (those are heavy and absent from the lean CI image); a
rolling forecast + residual sigma is robust on the short weekly series Helios works with.
"""
from __future__ import annotations
from dataclasses import dataclass
from statistics import mean, pstdev

from scipy.stats import norm

DEFAULT_K = 4              # rolling-forecast window (recent points)
DEFAULT_Z = 2.5           # |z| above this => anomaly
MIN_HISTORY = 3           # need this many points before scoring


@dataclass
class AnomalyPoint:
    index: int
    value: float
    forecast: float | None
    sigma: float
    z: float
    is_anomaly: bool


def _onestep_forecast(values: list[float], t: int, k: int) -> float:
    """Forecast point t from the mean of the up-to-k points before it."""
    window = values[max(0, t - k):t]
    return mean(window) if window else values[t]


def _sigma(values: list[float], k: int, floor_frac: float = 0.01) -> float:
    """Residual std of the one-step forecasts, with a floor so a flat series doesn't
    divide by zero (the floor is a small fraction of the series level)."""
    resid = [values[t] - _onestep_forecast(values, t, k) for t in range(1, len(values))]
    s = pstdev(resid) if len(resid) >= 2 else 0.0
    level = abs(mean(values)) if values else 0.0
    return max(s, floor_frac * level, 1e-12)


def detect_anomaly(values: list[float], *, k: int = DEFAULT_K, z_threshold: float = DEFAULT_Z,
                   min_history: int = MIN_HISTORY) -> list[AnomalyPoint]:
    """Score each point against a rolling forecast; flag those with |z| > z_threshold.
    Points before `min_history` aren't scored (not enough history)."""
    sigma = _sigma(values, k)
    out: list[AnomalyPoint] = []
    for t in range(len(values)):
        if t < min_history:
            out.append(AnomalyPoint(t, values[t], None, sigma, 0.0, False))
            continue
        fc = _onestep_forecast(values, t, k)
        z = (values[t] - fc) / sigma
        out.append(AnomalyPoint(t, values[t], fc, sigma, z, abs(z) > z_threshold))
    return out


def forecast_next(values: list[float], *, k: int = DEFAULT_K, conf: float = 0.95) -> dict:
    """Point forecast + prediction interval for the NEXT value after the series."""
    if not values:
        raise ValueError("need at least one observation to forecast")
    fc = mean(values[-k:])
    sigma = _sigma(values, k)
    z = norm.ppf(1 - (1 - conf) / 2)
    return {"forecast": fc, "lower": fc - z * sigma, "upper": fc + z * sigma,
            "sigma": sigma, "conf": conf}
