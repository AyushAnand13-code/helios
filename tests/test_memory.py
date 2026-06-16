"""Memory tests — the seasonality calendar, the store, and the suppression decision that
keeps the autonomous run from re-paging the team. Pure-Python; offline.
Run: pytest tests/test_memory.py -v
"""
from types import SimpleNamespace

import pytest

from helios.memory import MemoryStore, DiagnosisRecord, decide, finding_key
from helios.memory.seasonality import SeasonalityCalendar


def _diag(*, delta=-0.012, dominant="rate", segment="Referral / desktop",
          w1="2020-12-07", significant=True):
    return SimpleNamespace(w0="2020-11-30", w1=w1, delta=delta, dominant=dominant,
                           significant=significant, revenue_at_risk=-40_000.0,
                           drivers=[{"segment": segment}])


def _report(verdict="SHIP"):
    return SimpleNamespace(verdict=verdict, failures=[])


# ── seasonality calendar ──────────────────────────────────────────────────────────
def test_calendar_flags_seasonal_weeks_and_clears_normal_ones():
    cal = SeasonalityCalendar()
    assert cal.event_for_week("2020-11-23").name == "Black Friday"   # week contains 11-27
    assert cal.event_for_week("2021-01-04").name.startswith("Post-holiday")
    assert cal.event_for_week("2020-12-07") is None                  # an ordinary week


# ── store ─────────────────────────────────────────────────────────────────────────
def test_store_saves_and_recalls_by_key(tmp_path):
    store = MemoryStore(tmp_path / "m.jsonl")
    d = _diag()
    store.save_diagnosis(DiagnosisRecord.from_diagnosis(d, as_of="2020-12-07", verdict="SHIP"))
    key = finding_key("rate", "Referral / desktop", -0.012)
    assert len(store.recall_prior(key)) == 1
    assert store.recall_prior(key, as_of="2021-06-01", within_days=14) == []  # too old


# ── suppression decisions ─────────────────────────────────────────────────────────
def test_fresh_material_finding_is_new(tmp_path):
    dec = decide(_diag(), _report("SHIP"), as_of="2020-12-07", store=MemoryStore(tmp_path / "m.jsonl"))
    assert dec.status == "NEW" and dec.suppress is False


def test_new_then_repeat_cycle(tmp_path):
    store = MemoryStore(tmp_path / "m.jsonl")
    d, rep = _diag(), _report("SHIP")
    first = decide(d, rep, as_of="2020-12-07", store=store)
    assert first.status == "NEW"
    store.save_diagnosis(DiagnosisRecord.from_diagnosis(d, as_of="2020-12-07", verdict="SHIP"))
    second = decide(d, rep, as_of="2020-12-08", store=store)   # next day, same finding
    assert second.status == "REPEAT" and second.suppress is True


def test_seasonal_week_is_suppressed(tmp_path):
    dec = decide(_diag(w1="2020-11-23"), _report("SHIP"), as_of="2020-11-30",
                 store=MemoryStore(tmp_path / "m.jsonl"))
    assert dec.status == "SEASONAL" and dec.suppress is True


def test_refuted_finding_is_suppressed(tmp_path):
    rep = SimpleNamespace(verdict="REFUTE",
                          failures=[SimpleNamespace(detail="does not reconcile")])
    dec = decide(_diag(), rep, as_of="2020-12-07", store=MemoryStore(tmp_path / "m.jsonl"))
    assert dec.status == "REFUTED" and dec.suppress is True


def test_immaterial_move_is_suppressed(tmp_path):
    dec = decide(_diag(delta=-0.0001), _report("REVISE"), as_of="2020-12-07",
                 store=MemoryStore(tmp_path / "m.jsonl"))
    assert dec.status == "IMMATERIAL" and dec.suppress is True
