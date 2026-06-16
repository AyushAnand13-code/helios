"""Autonomous-run (heartbeat) tests — the scheduled run must produce a complete, dated
Decision Brief from the synthetic source with no BigQuery and no LLM. Skipped where
pandas isn't installed (the lean CI image). Run: pytest tests/test_run.py -v
"""
from datetime import date

import pytest

pytest.importorskip("pandas")  # the synthetic weekly loader needs pandas

from helios.run import generate  # noqa: E402

END = date(2021, 1, 31)


def test_brief_is_written_with_all_sections(tmp_path):
    r = generate(source="synthetic", out_dir=tmp_path, as_of="2021-01-31", end_date=END)
    assert r.diagnosis is not None and r.report is not None
    assert r.report.verdict in {"SHIP", "REVISE", "REFUTE"}
    assert r.path is not None and r.path.exists()
    md = r.path.read_text(encoding="utf-8")
    for section in ("# Helios Decision Brief", "## Headline", "## Why it moved",
                    "## Top driver segments", "## Dollar impact",
                    "## Recommended action", "Critic verdict"):
        assert section in md, f"missing section: {section}"


def test_handles_too_little_data_gracefully(tmp_path):
    # A 3-day window is a single ISO week -> nothing to compare; must not crash.
    r = generate(source="synthetic", out_dir=tmp_path, days=3, as_of="2021-01-31", end_date=END)
    assert r.diagnosis is None
    assert r.path is None
    assert "Not enough data" in r.note


def test_run_is_deterministic(tmp_path):
    a = generate(source="synthetic", out_dir=tmp_path / "a", as_of="2021-01-31", end_date=END)
    b = generate(source="synthetic", out_dir=tmp_path / "b", as_of="2021-01-31", end_date=END)
    assert a.markdown == b.markdown


def test_unknown_source_rejected(tmp_path):
    with pytest.raises(ValueError):
        generate(source="csv", out_dir=tmp_path)
