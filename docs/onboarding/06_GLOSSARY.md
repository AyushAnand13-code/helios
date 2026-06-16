# 6. Glossary — every term decoded

Plain definitions of every piece of jargon in the project, with the one-line interview phrasing.
Skim it; come back when a word trips you up.

### The scary tagline, decoded word by word
> "Governed mix-vs-rate funnel diagnosis on real GA4 data — no LLM-written SQL, no in-prose math."

- **Governed** = everything comes from approved, single-source definitions (the semantic layer),
  not made up on the fly.
- **mix-vs-rate** = it separates a traffic-composition change from a real behaviour change (the
  core idea, doc 02).
- **funnel diagnosis** = it figures out which step of the shopping funnel moved and why.
- **on real GA4 data** = real Google Analytics e-commerce data, not a toy dataset.
- **no LLM-written SQL** = the AI never writes database queries itself (a governed tool does).
- **no in-prose math** = the AI never calculates a number in its text (tested Python does).

### Concepts
- **Funnel** — the steps a shopper takes: visit → view product → add to cart → checkout → pay.
- **Conversion rate** — fraction who complete a step (e.g. session conversion = buyers ÷ visits).
- **Session** — one visit; all of a user's events grouped into one browsing session.
- **Mix-shift** — the *composition* of traffic changed (more mobile, less desktop). Can move the
  overall number even if every segment is unchanged.
- **Rate-change** — a segment's *own* conversion actually changed (real behaviour change).
- **Simpson's paradox** — the statistical trap where the overall number moves opposite to every
  subgroup, because of mix. The thing mix-vs-rate decomposition defends against.
- **Decomposition** — splitting a total change into additive parts (mix + rate + interaction).
- **Significance / p-value** — a stats test of "is this move real or just noise?" Small p (< 0.05)
  = real.
- **Revenue at risk** — the dollar value of the move (`rate effect × sessions × avg order value`).
- **A/B test / experiment** — splitting traffic into two groups to test a change. **Power
  analysis** = computing how many people you need to detect an effect (the "sample size").
- **Anomaly detection / forecasting** — predicting the expected value and flagging when reality
  deviates too far. Used to pick which week to investigate.
- **Seasonality** — predictable calendar effects (Black Friday, post-holiday January slump). The
  system suppresses these so it doesn't "alert" on Black Friday.

### Data & engineering tools
- **GA4 (Google Analytics 4)** — Google's website-analytics product; the source of the raw events.
- **BigQuery** — Google's cloud data warehouse (a big, fast SQL database) where the data lives and
  queries run. Tables are named `project.dataset.table`.
- **dbt (data build tool)** — transforms raw data into clean, tested tables with SQL, in layers
  (staging → intermediate → marts).
- **Star schema / fact & dimension tables** — a standard warehouse design: `fct_` tables hold the
  measurements (events, orders), `dim_` tables hold the descriptive lookups (channels, dates).
- **Mart** — a final, clean, business-ready table (e.g. `fct_funnel`).
- **Semantic layer / metric registry** — one file that defines every metric and dimension once, in
  SQL, so the whole system agrees on definitions.
- **Materialization** — how dbt stores a model (a `view` = a saved query; a `table` = physical
  rows).
- **Reconciliation** — checking a computed total matches the source to confirm correctness.

### AI / app tools
- **LLM (Large Language Model)** — an AI like Gemini or Claude that generates text. In Helios it
  writes the *prose* of the brief, never the numbers.
- **MCP (Model Context Protocol)** — an open standard for giving an AI a controlled set of **tools**
  (functions) it may call. Helios exposes its governed logic as MCP tools.
- **Grounding** — forcing every number in AI output to come from a real tool call, never invented.
- **Agent** — a role in the pipeline (Monitor, Critic, …) allowed to use only certain tools.
- **The Critic** — the agent that tries to *disprove* a finding before it ships (verify-then-trust).
- **Allow-list** — the set of tools an agent is permitted to call (enforced in code).
- **Streamlit** — a Python library for building data web apps quickly; our dashboard.
- **Claude Code** — Anthropic's AI coding tool (what you used to build this). See doc 07 on how to
  talk about it.

### Project-specific names
- **Helios** — the project: the autonomous growth-diagnosis engine.
- **Decision Brief** — the short executive report Helios produces.
- **Decompose / decompose_change** — the core mix/rate math function.
- **fct_funnel** — the main session-grain table the diagnosis reads.
- **helios_dev_marts** — the BigQuery dataset where the dbt marts live.

Next: **[07_INTERVIEW_PLAYBOOK.md](07_INTERVIEW_PLAYBOOK.md)** — how to present and own it.
