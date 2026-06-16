"""Agent layer tests — the governance that matters: per-agent tool allow-lists are
enforced, and the plan-execute-critique loop runs with the Critic as a gate.
Run: pytest tests/test_agents.py -v
"""
from datetime import date

import pytest

from helios.agents import Toolbox, AllowListError, orchestrate
from helios.agents.roles import allows, AGENTS

SEGS = [
    {"segment": "A", "num_t0": 25, "den_t0": 500, "num_t1": 22.0, "den_t1": 440},
    {"segment": "B", "num_t0": 10, "den_t0": 500, "num_t1": 11.2, "den_t1": 560},
]


# ── allow-lists (Bible §18.9) ─────────────────────────────────────────────────────
def test_narrator_cannot_touch_bigquery():
    tb = Toolbox()
    with pytest.raises(AllowListError):
        tb.call("Narrator", "run_query", "SELECT 1")     # the canonical forbidden call
    with pytest.raises(AllowListError):
        tb.call("Narrator", "decompose_change", SEGS)    # Narrator does no math (G2)


def test_decompose_agent_can_only_decompose():
    tb = Toolbox()
    res = tb.call("Decompose", "decompose_change", SEGS)  # allowed
    assert res.dominant_effect in {"mix", "rate", "interaction"}
    with pytest.raises(AllowListError):
        tb.call("Decompose", "significance_test", 25, 500, 22, 440)  # not on its list


def test_allow_list_table_is_sane():
    assert allows("Decompose", "decompose_change")
    assert not allows("Narrator", "run_query")
    assert allows("Critic", "critique")
    # Narrator has no data/math tools at all.
    assert not (AGENTS["Narrator"]["allow"] & {"run_query", "decompose_change",
                                               "significance_test", "build_query"})


def test_trace_records_calls():
    tb = Toolbox()
    tb.call("Decompose", "decompose_change", SEGS)
    assert tb.trace and tb.trace[0].agent == "Decompose" and tb.trace[0].tool == "decompose_change"


# ── the loop ──────────────────────────────────────────────────────────────────────
def _df_two_weeks(rows_by_week):
    pd = pytest.importorskip("pandas")
    cols = ["sessions", "view_item_sessions", "add_to_cart_sessions", "begin_checkout_sessions",
            "add_shipping_info_sessions", "add_payment_info_sessions", "purchasing_sessions"]
    rows = []
    for wk, cells in rows_by_week.items():
        for ch, dev, sess, pur in cells:
            rows.append({"week": wk, "channel_group": ch, "device_category": dev,
                         "sessions": sess, "view_item_sessions": int(sess * 0.6),
                         "add_to_cart_sessions": int(sess * 0.3),
                         "begin_checkout_sessions": int(sess * 0.15),
                         "add_shipping_info_sessions": int(sess * 0.12),
                         "add_payment_info_sessions": int(sess * 0.1),
                         "purchasing_sessions": pur, "revenue": pur * 60.0})
    return pd.DataFrame(rows)


def test_orchestrate_ships_a_real_rate_finding(tmp_path):
    from helios.memory import MemoryStore
    # w1 (2021-01-25, outside any seasonal window): a big mobile conversion drop.
    df = _df_two_weeks({
        "2021-01-18": [("Direct", "mobile", 40000, 1200), ("Direct", "desktop", 20000, 700)],
        "2021-01-25": [("Direct", "mobile", 40000, 600), ("Direct", "desktop", 20000, 700)],
    })
    res = orchestrate(df, as_of="2021-01-25", source_label="test",
                      store=MemoryStore(tmp_path / "m.jsonl"))
    assert res.diagnosis.dominant == "rate"
    assert res.report.verdict in {"SHIP", "REVISE"}
    assert res.status == "NEW" and res.gate == "SHIPPED"
    # the governed steps went through the toolbox, in order
    t = res.trace_str()
    assert "Decompose:decompose_change" in t and "Critic:critique" in t
    assert "Narrator:render_brief" in t and "Orchestrator:save_diagnosis" in t
    assert "## Recommended experiment" in res.markdown   # Prescribe's output


def test_critic_gate_holds_an_immaterial_finding(tmp_path):
    from helios.memory import MemoryStore
    # identical weeks -> no real move -> immaterial -> gate must HOLD, not ship
    same = [("Direct", "mobile", 40000, 1000), ("Direct", "desktop", 20000, 600)]
    df = _df_two_weeks({"2021-01-18": same, "2021-01-25": same})
    res = orchestrate(df, as_of="2021-01-25", source_label="test",
                      store=MemoryStore(tmp_path / "m.jsonl"))
    assert res.status == "IMMATERIAL" and res.gate == "HELD"
