"""Helios — Growth Diagnosis dashboard (Streamlit).

Presents the autonomous mix-vs-rate funnel diagnosis: it is a VIEWER for the Decision
Brief, not an ad-hoc BI tool. Run:  streamlit run app.py
Needs the dbt marts built and `gcloud auth application-default login` done.
"""
from __future__ import annotations
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from datetime import date

from helios.diagnosis import (load_weekly, weeks_in, biggest_move, most_anomalous_move,
                              run_diagnosis, FUNNEL_STEPS)
from helios.critic import critique
from helios.report.brief_md import recommended_experiment
from helios.memory import decide

st.set_page_config(page_title="Helios — Growth Diagnosis", layout="wide")

# ---- look & feel: modern dark, multi-colour, presentation-ready ----
st.markdown(
    """
    <style>
      /* glassy metric cards with a neon top stripe */
      [data-testid="stMetric"] {
        background: linear-gradient(145deg, #161D30 0%, #0E1422 100%);
        border: 1px solid #242C42;
        border-radius: 14px;
        padding: 18px 18px 14px;
        box-shadow: 0 6px 24px rgba(0,0,0,0.45);
        position: relative; overflow: hidden;
      }
      [data-testid="stMetric"]::before {
        content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px;
        background: linear-gradient(90deg, #22D3EE 0%, #7C5CFF 50%, #F472B6 100%);
      }
      [data-testid="stMetricValue"] { color: #F4F6FC; font-weight: 700; }
      [data-testid="stMetricLabel"] p { color: #9AA6C4; font-weight: 600; }
      h3 { color: #A78BFA; padding-top: .35rem; letter-spacing: .2px; }
      .stButton > button {
        border: 0; border-radius: 11px; font-weight: 700; color: #fff;
        background: linear-gradient(135deg, #7C5CFF 0%, #DB2777 100%);
      }
      .stButton > button:hover { filter: brightness(1.1); }
      [data-testid="stExpander"] { border-radius: 11px; border-color: #242C42; }
      a { color: #38BDF8; }
    </style>
    """,
    unsafe_allow_html=True,
)

REGISTRY_PATH = Path(__file__).resolve().parent / "semantic" / "semantic_layer.yaml"


def _gemini_key() -> str | None:
    """Gemini key from Streamlit secrets (cloud) or env var (local)."""
    try:
        k = st.secrets["GEMINI_API_KEY"]
        if k:
            return k
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


@st.cache_resource(show_spinner=False)
def get_client(project: str):
    """BigQuery client. On Streamlit Cloud, auth via a [gcp_service_account] secret;
    locally, fall back to your gcloud Application Default Credentials."""
    from google.cloud import bigquery
    try:
        info = dict(st.secrets["gcp_service_account"])  # set in Streamlit Cloud secrets
    except Exception:
        info = None
    if info:
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_info(info)
        return bigquery.Client(credentials=creds, project=project or creds.project_id)
    return bigquery.Client(project=project) if project else bigquery.Client()


@st.cache_data(ttl=600, show_spinner="Loading funnel data from BigQuery…")
def get_data(project: str, dataset: str):
    return load_weekly(get_client(project), project, dataset)


# ---- header banner ----
st.markdown(
    """
    <div style="background: linear-gradient(120deg,#4F46E5 0%,#7C3AED 28%,#DB2777 64%,#06B6D4 100%);
                padding: 1.7rem 1.9rem; border-radius: 18px; margin-bottom: 1.3rem;
                box-shadow: 0 10px 34px rgba(124,58,237,0.40);">
      <div style="color:#fff; font-size:2.2rem; font-weight:800; letter-spacing:.3px;
                  text-shadow: 0 2px 10px rgba(0,0,0,0.25);">
        Helios — Autonomous Growth Diagnosis</div>
      <div style="color:#EEF0FF; font-size:1.05rem; margin-top:.4rem; opacity:.95;">
        Governed mix-vs-rate funnel diagnosis on real GA4 data — no LLM-written SQL, no in-prose math.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---- sidebar: data source ----
with st.sidebar:
    st.header("Data source")
    project = st.text_input("GCP project", os.environ.get("HELIOS_PROJECT", "helios-mvp"))
    dataset = st.text_input("Marts dataset", os.environ.get("HELIOS_MARTS_DATASET", "helios_dev_marts"))

try:
    df = get_data(project, dataset)
except Exception as e:  # noqa: BLE001
    st.error(f"Couldn't load data from `{project}.{dataset}.fct_funnel`.\n\n{e}\n\n"
             "Have you run `dbt build` and `gcloud auth application-default login`?")
    st.stop()

weeks = weeks_in(df)
if len(weeks) < 2:
    st.warning("Need at least two weeks of data to compare.")
    st.stop()

auto0, auto1 = biggest_move(df)
fc0, fc1 = most_anomalous_move(df)

with st.sidebar:
    st.header("Compare weeks")
    mode = st.radio("Week selection",
                    ["Forecast-flagged anomaly", "Biggest week-over-week move", "Manual"],
                    index=0,
                    help="Forecast-based detection ignores low-volume boundary weeks whose "
                         "rate is normal — unlike the raw biggest move.")
    if mode == "Forecast-flagged anomaly":
        w0, w1 = fc0, fc1
        st.caption(f"Anomaly flagged: **{w0} → {w1}**")
    elif mode == "Biggest week-over-week move":
        w0, w1 = auto0, auto1
        st.caption(f"Biggest move: **{w0} → {w1}**")
    else:
        w0 = st.selectbox("Baseline week", weeks, index=weeks.index(auto0))
        later = [w for w in weeks if w > w0] or [weeks[-1]]
        w1 = st.selectbox("Compare week", later,
                          index=later.index(auto1) if auto1 in later else 0)

d = run_diagnosis(df, w0, w1)
report = critique(d)                                        # verify-then-trust
decision = decide(d, report, as_of=date.today().isoformat(), store=None)

# ---- headline metrics ----
direction = "drop" if d.delta < 0 else "rise"
st.subheader(f"Session conversion {direction}:  {w0}  →  {w1}")

# Critic verdict + what the autonomous run would do with this finding.
_verdict_box = {"SHIP": st.success, "REVISE": st.warning, "REFUTE": st.error}.get(
    report.verdict, st.info)
_verdict_box(
    f"**Critic verdict: {report.verdict}**  ·  Autonomous status: **{decision.status}** — "
    + ("a fresh, material finding — the daily run would alert the team."
       if decision.status == "NEW" else f"the run would suppress this ({decision.reason})."))

c1, c2, c3, c4 = st.columns(4)
c1.metric("Conversion — baseline", f"{d.conv_t0 * 100:.2f}%")
c2.metric("Conversion — compare", f"{d.conv_t1 * 100:.2f}%", f"{d.delta * 100:+.2f} pts")
c3.metric("p-value", f"{d.p_value:.1e}")
c4.metric("Revenue at risk", f"${d.revenue_at_risk:,.0f}")

if d.significant:
    st.success(f"**Statistically significant** (p = {d.p_value:.1e} < 0.05).")
else:
    st.warning(f"Not statistically significant (p = {d.p_value:.1e}) — monitor, don't act yet.")

# ---- why it moved: mix vs rate ----
st.markdown("### Why it moved — mix-shift vs rate-change")
why = pd.DataFrame(
    {"effect": ["mix (composition)", "rate (behaviour)", "interaction"],
     "points": [d.mix * 100, d.rate * 100, d.interaction * 100]}
)
st.bar_chart(why, x="effect", y="points", color="effect", height=240)

if d.dominant == "mix":
    st.info("**Dominant effect: MIX** — your traffic composition shifted between segments that "
            "convert differently. The funnel itself may be fine; don't 'fix checkout' blindly.")
else:
    st.info("**Dominant effect: RATE** — a real in-segment behaviour change. Worth a funnel / UX "
            "investigation in the top driver segment below.")

# ---- Critic review (verify-then-trust) ----
st.markdown("### Critic review — verify-then-trust")
st.caption("Every finding is attacked before it ships: reconcile (does the decomposition add "
           "up?), materiality, significance, honest mix-vs-rate framing, dollar bounds, and a "
           "funnel data-quality check.")
_icons = {"PASS": "✅", "WARN": "⚠️", "FAIL": "⛔"}
critic_df = pd.DataFrame([
    {"": _icons.get(c.status, ""), "Check": c.name, "Detail": c.detail}
    for c in report.checks])
st.dataframe(critic_df, hide_index=True, use_container_width=True)

# ---- funnel + drivers ----
left, right = st.columns([1, 1.3])

with left:
    st.markdown(f"### Funnel — {w1}")
    fdf = pd.DataFrame(
        {"sessions": [d.funnel_t1[lbl] for _, lbl in FUNNEL_STEPS]},
        index=[lbl for _, lbl in FUNNEL_STEPS],
    )
    st.bar_chart(fdf, height=300)

with right:
    st.markdown("### Top driver segments")
    dd = pd.DataFrame(d.drivers).rename(columns={
        "segment": "Segment", "total_pts": "Total Δ (pts)", "mix_pts": "Mix (pts)",
        "rate_pts": "Rate (pts)", "conv_t0_pct": "Conv before %", "conv_t1_pct": "Conv after %",
    })
    st.dataframe(
        dd.style.format({
            "Total Δ (pts)": "{:+.3f}", "Mix (pts)": "{:+.3f}", "Rate (pts)": "{:+.3f}",
            "Conv before %": "{:.2f}", "Conv after %": "{:.2f}",
        }),
        hide_index=True, use_container_width=True,
    )

# ---- recommended action ----
st.markdown("### Recommended action")
if not d.significant:
    st.write("Move is not statistically significant — **monitor**, do not act yet.")
elif d.dominant == "mix":
    st.write("Investigate the **traffic-mix shift** (acquisition / channel changes), not the funnel.")
else:
    top = d.drivers[0]["segment"] if d.drivers else "the top segment"
    st.write(f"Drill the rate change in **{top}** — run a funnel-step diagnosis and a targeted "
             f"experiment there; it carries the largest in-segment behaviour move "
             f"(**${d.revenue_at_risk:,.0f}** at risk this week).")

# ---- recommended experiment (powered) ----
_exp = recommended_experiment(d) if (report.verdict != "REFUTE" and d.dominant == "rate") else None
if _exp is not None:
    st.markdown("### Recommended experiment (powered)")
    st.write(f"**Hypothesis:** {_exp.hypothesis}")
    e1, e2, e3 = st.columns(3)
    e1.metric("Sample size / arm", f"{_exp.n_per_arm:,}")
    e2.metric("Runtime", f"~{_exp.runtime_days} days" if _exp.runtime_days is not None else "n/a")
    e3.metric("Feasible (≤6 wks)?", "Yes" if _exp.feasible else "Slow")
    st.caption(f"{_exp.arms}-arm {_exp.split} split · detect +{_exp.mde_rel * 100:.0f}% at "
               f"alpha={_exp.alpha}, power={_exp.power:.0%} · primary "
               f"`{_exp.primary_metric}` · guardrails: "
               + ", ".join(f"`{g}`" for g in _exp.guardrails)
               + ". Sized via two-proportion power analysis (`helios.experiment`).")

# ---- grounded AI Decision Brief (v1) ----
st.divider()
st.markdown("### AI Decision Brief")
st.caption("An LLM (Gemini) writes the executive brief by **calling the governed tools** — "
           "it never writes SQL or computes a statistic. Every figure traces to a tool output.")

key = _gemini_key()
if not key:
    st.info("Set a **GEMINI_API_KEY** to enable the AI brief — a Streamlit *secret* on the "
            "cloud, or an env var locally. Get a free key at https://aistudio.google.com/apikey")
else:
    if st.button("Generate AI brief", type="primary"):
        with st.spinner("Gemini is calling governed tools and writing the brief…"):
            try:
                from helios.llm.brief import generate_decision_brief
                st.session_state["brief"] = generate_decision_brief(
                    df, str(REGISTRY_PATH), key, focus_weeks=(w0, w1))
            except Exception as e:  # noqa: BLE001
                st.session_state["brief"] = None
                st.error(f"Brief generation failed: {e}")
    res = st.session_state.get("brief")
    if res:
        st.markdown(res.text)
        with st.expander("Grounding — the governed tools the model called"):
            for c in res.tool_calls:
                st.write(f"• `{c}`")
            st.caption(f"Model: {res.model}. No SQL authored by the LLM; no stat computed in prose.")

# ---- honest benchmark: Helios vs naive baseline ----
st.divider()
st.markdown("### Benchmark — Helios vs a naive baseline")
st.caption("Honest offline eval: we inject **known** funnel anomalies (rate-changes and "
           "mix-shifts) into the real segment mix, then check which method recovers the true "
           "cause. The naive 'largest-segment-delta' baseline is structurally blind to "
           "mix-shifts — that's where the governed decomposition earns its keep.")
try:
    from helios.eval.runner import base_segments_from_df, score_benchmark
    bench = score_benchmark(base_segments_from_df(df))
    bc1, bc2 = st.columns(2)
    bc1.metric("Helios accuracy (segment + effect)",
               f"{bench.helios_effect_acc * 100:.0f}%",
               f"{bench.helios_effect_correct}/{bench.n} scenarios")
    bc2.metric("Naive baseline accuracy",
               f"{bench.baseline_segment_acc * 100:.0f}%",
               f"{bench.baseline_segment_correct}/{bench.n} scenarios", delta_color="off")
    with st.expander("Per-scenario results"):
        bdf = pd.DataFrame(bench.rows)[
            ["scenario", "truth_effect", "helios_correct", "baseline_correct"]
        ].rename(columns={"scenario": "Injected scenario", "truth_effect": "True cause",
                          "helios_correct": "Helios ✓", "baseline_correct": "Naive ✓"})
        st.dataframe(bdf, hide_index=True, use_container_width=True)
    st.caption("Controlled-attribution accuracy (we know the injected cause) — it proves we "
               "recover the right driver, not causation.")
except Exception as e:  # noqa: BLE001
    st.warning(f"Benchmark unavailable: {e}")

with st.expander("How is this computed?"):
    st.markdown(
        "- **Data**: governed query composed from the registry by `semantic-mcp.build_query` over "
        "`fct_funnel` (session grain), dry-run cost-checked by `warehouse-mcp` — no hand-written SQL.\n"
        "- **Week selection**: forecast-based anomaly detection on the conversion-rate series "
        "(`helios.stats.detect_anomaly`), robust to partial boundary weeks.\n"
        "- **Decomposition**: `ΔR = mix + rate + interaction` (`helios.stats.decompose_change`), the "
        "Simpson's-paradox-safe split of the aggregate conversion change.\n"
        "- **Significance**: pooled two-proportion z-test (`helios.stats.two_proportion_ztest`).\n"
        "- **Critic**: every finding is attacked (reconcile / significance / framing / dollars / "
        "data-quality) before it ships (`helios.critic`).\n"
        "- **Experiment**: a powered A/B test sized via two-proportion power analysis "
        "(`helios.experiment`).\n"
        "- **AI brief**: an LLM calls the governed tools above (grounding) — it never writes SQL "
        "or computes a statistic itself."
    )
