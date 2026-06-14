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

from helios.diagnosis import load_weekly, weeks_in, biggest_move, run_diagnosis, FUNNEL_STEPS

st.set_page_config(page_title="Helios — Growth Diagnosis", page_icon="📉", layout="wide")

REGISTRY_PATH = Path(__file__).resolve().parent / "models" / "semantic" / "semantic_layer.yaml"


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


# ---- header ----
st.title("📉 Helios — Autonomous Growth Diagnosis")
st.caption("Governed mix-vs-rate funnel diagnosis on the GA4 Google Merchandise Store. "
           "Every number is a governed-mart + deterministic-stats output — no LLM, no hand-written SQL.")

# ---- sidebar: data source ----
with st.sidebar:
    st.header("⚙️ Data source")
    project = st.text_input("GCP project", os.environ.get("HELIOS_PROJECT", "helios-mvp"))
    dataset = st.text_input("Marts dataset", os.environ.get("HELIOS_MARTS_DATASET", "helios_dev"))

try:
    df = get_data(project, dataset)
except Exception as e:  # noqa: BLE001
    st.error(f"Couldn't load data from `{project}.{dataset}.fct_daily_funnel`.\n\n{e}\n\n"
             "Have you run `dbt build` and `gcloud auth application-default login`?")
    st.stop()

weeks = weeks_in(df)
if len(weeks) < 2:
    st.warning("Need at least two weeks of data to compare.")
    st.stop()

auto0, auto1 = biggest_move(df)

with st.sidebar:
    st.header("📅 Compare weeks")
    use_auto = st.checkbox("Auto: biggest week-over-week move", value=True)
    if use_auto:
        w0, w1 = auto0, auto1
        st.caption(f"Biggest move detected: **{w0} → {w1}**")
    else:
        w0 = st.selectbox("Baseline week", weeks, index=weeks.index(auto0))
        later = [w for w in weeks if w > w0] or [weeks[-1]]
        w1 = st.selectbox("Compare week", later,
                          index=later.index(auto1) if auto1 in later else 0)

d = run_diagnosis(df, w0, w1)

# ---- headline metrics ----
direction = "drop" if d.delta < 0 else "rise"
st.subheader(f"Session conversion {direction}:  {w0}  →  {w1}")

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
).set_index("effect")
st.bar_chart(why, height=220)

if d.dominant == "mix":
    st.info("**Dominant effect: MIX** — your traffic composition shifted between segments that "
            "convert differently. The funnel itself may be fine; don't 'fix checkout' blindly.")
else:
    st.info("**Dominant effect: RATE** — a real in-segment behaviour change. Worth a funnel / UX "
            "investigation in the top driver segment below.")

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
st.markdown("### ✅ Recommended action")
if not d.significant:
    st.write("Move is not statistically significant — **monitor**, do not act yet.")
elif d.dominant == "mix":
    st.write("Investigate the **traffic-mix shift** (acquisition / channel changes), not the funnel.")
else:
    top = d.drivers[0]["segment"] if d.drivers else "the top segment"
    st.write(f"Drill the rate change in **{top}** — run a funnel-step diagnosis and a targeted "
             f"experiment there; it carries the largest in-segment behaviour move "
             f"(**${d.revenue_at_risk:,.0f}** at risk this week).")

# ---- grounded AI Decision Brief (v1) ----
st.divider()
st.markdown("### 🧠 AI Decision Brief")
st.caption("An LLM (Gemini) writes the executive brief by **calling the governed tools** — "
           "it never writes SQL or computes a statistic. Every figure traces to a tool output.")

key = _gemini_key()
if not key:
    st.info("Set a **GEMINI_API_KEY** to enable the AI brief — a Streamlit *secret* on the "
            "cloud, or an env var locally. Get a free key at https://aistudio.google.com/apikey")
else:
    if st.button("✍️ Generate AI brief", type="primary"):
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
        with st.expander("🔎 Grounding — the governed tools the model called"):
            for c in res.tool_calls:
                st.write(f"• `{c}`")
            st.caption(f"Model: {res.model}. No SQL authored by the LLM; no stat computed in prose.")

# ---- honest benchmark: Helios vs naive baseline ----
st.divider()
st.markdown("### 📊 Benchmark — Helios vs a naive baseline")
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
        "- **Data**: `fct_daily_funnel` (governed dbt mart), sliced by `channel_group × device_category`.\n"
        "- **Decomposition**: `ΔR = mix + rate + interaction` (`helios.stats.decompose_change`), the "
        "Simpson's-paradox-safe split of the aggregate conversion change.\n"
        "- **Significance**: pooled two-proportion z-test (`helios.stats.two_proportion_ztest`).\n"
        "- **Revenue at risk**: `rate_effect × sessions × AOV`.\n"
        "- **AI brief**: an LLM calls the governed tools above (grounding) — it never writes SQL "
        "or computes a statistic itself."
    )
