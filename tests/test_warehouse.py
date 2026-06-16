"""Warehouse tests — dry-run budget enforcement (G3), reconcile drift (G4), and the
rewired governed load_weekly. A fake BigQuery client keeps it offline; skipped where
google-cloud-bigquery isn't installed (the lean CI image needs it for QueryJobConfig).
Run: pytest tests/test_warehouse.py -v
"""
import pytest

pytest.importorskip("google.cloud.bigquery")  # dry_run builds a QueryJobConfig

from helios.warehouse import Warehouse, BudgetExceeded, BYTE_BUDGET_GIB  # noqa: E402

_GIB = 1024 ** 3


class _FakeJob:
    def __init__(self, bytes_processed=0, rows=None):
        self.total_bytes_processed = bytes_processed
        self._rows = rows or []

    def result(self):
        return self._rows


class _FakeClient:
    """Mimics bigquery.Client.query: dry-run calls read total_bytes_processed; real calls
    read .result(). Records the SQL it was handed."""
    def __init__(self, bytes_processed=0, rows=None):
        self.bytes_processed = bytes_processed
        self.rows = rows or []
        self.queries = []

    def query(self, sql, job_config=None):
        self.queries.append(sql)
        return _FakeJob(self.bytes_processed, self.rows)


def test_dry_run_reports_bytes_and_budget():
    wh = Warehouse(_FakeClient(bytes_processed=2 * _GIB))
    est = wh.dry_run("SELECT 1")
    assert est["gib"] == pytest.approx(2.0)
    assert est["within_budget"] is True
    assert est["budget_gib"] == BYTE_BUDGET_GIB


def test_run_query_refuses_over_budget():
    wh = Warehouse(_FakeClient(bytes_processed=int(6 * _GIB)))  # > 5 GiB budget
    with pytest.raises(BudgetExceeded):
        wh.run_query("SELECT * FROM huge")


def test_run_query_returns_rows_within_budget():
    rows = [{"week": "2021-01-04", "sessions": 100}]
    client = _FakeClient(bytes_processed=int(0.1 * _GIB), rows=rows)
    wh = Warehouse(client)
    assert wh.run_query("SELECT 1") == rows
    assert len(client.queries) == 2  # dry-run, then the real run


def test_reconcile_passes_within_tolerance_and_fails_past_it():
    ok = Warehouse.reconcile(10_000, 10_040)        # 0.4% drift
    bad = Warehouse.reconcile(10_000, 11_000)       # 9% drift
    assert ok["reconciles"] is True
    assert bad["reconciles"] is False


def test_load_weekly_uses_governed_sql_and_warehouse():
    # The rewired load_weekly must compose SQL via the registry (no fct_daily_funnel
    # hand-SQL) and pull it through the dry-run-gated warehouse.
    from helios.diagnosis import load_weekly, build_weekly_sql

    sql = build_weekly_sql("helios-mvp", "helios_dev")
    assert "COUNT(DISTINCT session_key) AS sessions" in sql
    assert "FROM `helios-mvp.helios_dev.fct_funnel`" in sql

    rows = [{"week": "2021-01-04", "channel_group": "Direct", "device_category": "mobile",
             "sessions": 1000, "view_item_sessions": 600, "add_to_cart_sessions": 300,
             "begin_checkout_sessions": 150, "add_shipping_info_sessions": 120,
             "add_payment_info_sessions": 100, "purchasing_sessions": 30, "revenue": 1800.0}]
    client = _FakeClient(bytes_processed=int(0.2 * _GIB), rows=rows)
    df = load_weekly(client, "helios-mvp", "helios_dev", warehouse=Warehouse(client))
    assert list(df["week"]) == ["2021-01-04"]
    assert int(df["purchasing_sessions"].iloc[0]) == 30
    # fct_funnel (session grain), not the old fct_daily_funnel pre-agg
    assert any("fct_funnel`" in q for q in client.queries)
