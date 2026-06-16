# 5. The dashboard, section by section

This is a walkthrough of the Streamlit dashboard (`streamlit run app.py`) — what every box,
number, and chart means, and what to *say* about each. The dashboard is a **viewer** for the
diagnosis; it doesn't compute anything new, it just shows the engine's output for a chosen pair
of weeks.

> Reminder: it's a "secondary drill-down surface." The real product is the daily autonomous
> run. The dashboard is the pretty window into it — great for a demo.

---

## Sidebar — Data source
- **GCP project** (`helios-mvp`) — your Google Cloud account (what gets billed for queries).
- **Marts dataset** (`helios_dev_marts`) — the folder of dbt-built tables inside that project.

Together they tell the app where to find the table `fct_funnel`, i.e.
`helios-mvp.helios_dev_marts.fct_funnel`. (Full explanation: [03_THE_DATA.md](03_THE_DATA.md).)
You'd change these only to point at a different dataset (e.g. `helios_live` synthetic data).

## Sidebar — Compare weeks
The diagnosis compares **two weeks**. Three ways to pick them:
- **Forecast-flagged anomaly** (default) — the app forecasts the expected conversion rate from
  recent weeks and picks the week that deviates most. This is smarter than just "biggest drop"
  because it ignores a low-traffic partial week whose *rate* is actually normal.
- **Biggest week-over-week move** — the simple "largest raw change" pick.
- **Manual** — choose the two weeks yourself.

> **Say:** *"It selects the week to investigate with forecast-based anomaly detection, so it
> flags genuinely abnormal weeks rather than boundary artifacts."*

---

## Status banner — Critic verdict + autonomous status
A coloured line like **"Critic verdict: SHIP · Autonomous status: NEW — would alert the team."**
- **Critic verdict**: `SHIP` (finding survived all checks), `REVISE` (ship with a caveat), or
  `REFUTE` (rejected — don't act).
- **Autonomous status**: what the *daily run* would do — `NEW` (fresh, material → alert),
  or suppressed as `SEASONAL` / `REPEAT` / `IMMATERIAL` (don't spam the team).

> **Say:** *"This shows what the autonomous run would do — it only pages the team on a fresh,
> material, Critic-approved finding; it suppresses repeats and known-seasonal moves."*

## Four headline metrics
- **Conversion — baseline / compare** — the overall session→purchase rate in each week, and the
  change in percentage points.
- **p-value** — the statistical-significance number. **Small (< 0.05) = the move is real, not
  noise.** (e.g. `7.9e-06` means about 0.0000079 — extremely significant.)
- **Revenue at risk** — the dollar value of the *rate* part of the move (`rate effect × sessions
  × average order value`). It's "how much this behaviour change is costing per week."

> **Say:** *"It doesn't just say conversion dropped — it tells me if the drop is statistically
> real and what it's worth in dollars."*

## "Why it moved — mix-shift vs rate-change" (the key chart)
A bar chart of the three components: **mix**, **rate**, **interaction** (see
[02_THE_CORE_IDEA.md](02_THE_CORE_IDEA.md)). Below it, a line tells you the **dominant** one:
- **RATE dominant** → a real behaviour change → worth a funnel/UX investigation.
- **MIX dominant** → just a traffic-composition shift → *don't* "fix the checkout"; look at
  acquisition.

> **This is the chart to spend time on in a demo.** It's the whole point of the project.

## Critic review (verify-then-trust)
A table of the six checks the Critic ran, each ✅/⚠️/⛔:
`reconcile` (does the math add up?), `materiality` (big enough to matter?), `significance`
(real, not noise?), `mix-vs-rate framing` (are we about to give the wrong advice?), `dollar
sanity` (is the $ figure plausible?), `data quality` (is the funnel internally consistent?).

> **Say:** *"Before any finding ships, a Critic attacks it on six fronts — including catching
> the 'you're about to recommend fixing the checkout when it's really a mix shift' mistake."*

## Funnel + Top driver segments
- **Funnel chart** — the step-by-step counts for the compare week (sessions → view → cart →
  checkout → purchase). Shows *where* the leak is.
- **Top driver segments table** — the channel×device cells that contributed most to the move,
  with their mix/rate split and before/after conversion. Shows *who* drove it.

## Recommended action + Recommended experiment (powered)
- **Action** — one concrete next step, consistent with the Critic's verdict.
- **Experiment** — a properly **sized A/B test**: the hypothesis, **sample size per arm**,
  **runtime** (e.g. ~40 days), and whether it's feasible. This is real statistics (a
  two-proportion power analysis), not a guess.

> **Say:** *"Every actionable finding ships with a powered A/B test — sample size and runtime
> computed, so the team knows exactly what to run and for how long."*

## AI Decision Brief (Gemini, grounded)
A button that asks an LLM (Gemini) to **write the executive brief** — but the model can only
call the governed tools, so every number traces to a tool. The expandable **"Grounding"**
section lists exactly which tools it called.

> **Say:** *"The LLM writes the narrative, but it can't invent a number — the grounding panel
> shows every figure traces to a governed tool call. I verified the LLM's numbers matched the
> deterministic engine exactly."*

## Benchmark — Helios vs a naive baseline
Shows Helios's accuracy at recovering a known injected cause vs a naïve "biggest-segment-delta"
method that's blind to mix-shifts.

> **Be precise (important honesty):** *"This is controlled-attribution accuracy — we inject a
> known cause and check we recover it. It proves the method recovers the injected driver and
> beats the naïve baseline; it is **not** a claim of real-world causal accuracy."* Say it this
> way and you're bulletproof; overclaim it and you're not.

Next: **[06_GLOSSARY.md](06_GLOSSARY.md)** — every term decoded.
