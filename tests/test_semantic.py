"""SemanticLayer tests — governed SQL composition (G1) and hard-error governance (G5).
Pure-Python; reads the real registry. Run: pytest tests/test_semantic.py -v
"""
import pytest

from helios.semantic import SemanticLayer, SemanticError
from helios.semantic.layer import Filter

WEEKLY_METRICS = ["sessions", "view_item_sessions", "add_to_cart_sessions",
                  "begin_checkout_sessions", "purchasing_sessions", "revenue"]


@pytest.fixture(scope="module")
def sl():
    return SemanticLayer()


def test_weekly_funnel_query_is_composed_from_the_registry(sl):
    sql = sl.build_query(WEEKLY_METRICS, ["week", "channel_group", "device_category"],
                         project="helios-mvp", dataset="helios_dev")
    # Composed only from registered definitions — nothing hand-typed.
    assert "DATE_TRUNC(event_date, WEEK(MONDAY)) AS week" in sql
    assert "COUNT(DISTINCT session_key) AS sessions" in sql
    assert "COUNTIF(reached_purchase) AS purchasing_sessions" in sql
    assert "SUM(session_revenue) AS revenue" in sql
    assert "FROM `helios-mvp.helios_dev.fct_funnel`" in sql
    assert "GROUP BY week, channel_group, device_category" in sql
    assert sql.strip().endswith("ORDER BY week")


def test_unknown_metric_is_a_hard_error(sl):
    with pytest.raises(SemanticError):
        sl.get_metric("clicks")
    with pytest.raises(SemanticError):
        sl.build_query(["clicks"], ["week"])


def test_unsupported_dimension_is_rejected(sl):
    # session-grain metric cannot be sliced by an item-grain dimension
    with pytest.raises(SemanticError):
        sl.build_query(["sessions"], ["item_name"])


def test_metrics_must_share_one_grain(sl):
    with pytest.raises(SemanticError):
        sl.build_query(["revenue", "gross_revenue"], ["week"])


def test_filters_render_safe_literals(sl):
    sql = sl.build_query(
        ["sessions"], ["week"],
        filters=[Filter("device_category", "=", "mobile"),
                 Filter("day", "BETWEEN", ["2020-11-01", "2021-01-31"]),
                 Filter("channel_group", "IN", ["Paid Search", "Display"])],
        dataset="helios_dev")
    assert "device_category = 'mobile'" in sql
    assert "event_date BETWEEN DATE '2020-11-01' AND DATE '2021-01-31'" in sql
    assert "channel_group IN ('Paid Search', 'Display')" in sql


def test_filter_dimension_must_be_governed(sl):
    with pytest.raises(SemanticError):
        sl.build_query(["sessions"], ["week"],
                       filters=[Filter("made_up_dim", "=", "x")])


def test_sql_injection_in_value_is_escaped(sl):
    sql = sl.build_query(["sessions"], ["week"],
                         filters=[Filter("device_category", "=", "x'; DROP TABLE t;--")])
    # The quote is doubled, so the payload stays inside a string literal.
    assert "'x''; DROP TABLE t;--'" in sql
