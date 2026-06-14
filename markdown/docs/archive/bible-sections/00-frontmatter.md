# Helios — Project Bible

**Autonomous Growth Diagnosis Engine**

**Version:** v1.0  **Date:** 2026-06-03

**Purpose.** This document is the authoritative, rebuild-from-scratch reference for Helios — an autonomous "AI Growth Analyst" that continuously diagnoses *why* an e-commerce funnel is moving, distinguishes mix-shift from rate-change, quantifies revenue-at-risk in dollars, prescribes a prioritized and statistically-defensible experiment backlog, and produces an executive Decision Brief, all grounded in governed SQL it writes, verifies, and is graded on by an offline evaluation benchmark. It is written so that an engineer with no prior context could reconstruct the entire system — data model, semantic layer, MCP tool surface, seven-agent orchestration, memory, evaluation harness, and roadmap — years from now. Where any section disagrees with the Canonical Reference Card below, the Reference Card (which mirrors the project Foundation spec) wins.

---

## How to Read This Document

The Bible is organized in 25 numbered sections grouped into nine thematic parts. Read it top-to-bottom for the full narrative, or jump by role:

- **New to Helios?** Read Part I (Strategy, §1–5) for the *why*, then the Canonical Reference Card in this front matter for the shared vocabulary. Those two together are enough to follow any later section.
- **Analytics / data engineer?** Focus on Part III (Data Model, §8–11), Part IV (Semantics, §12–14), and Part V (Analytics Engineering, §15–17). These define every metric, the dbt DAG, and the BigQuery cost controls.
- **AI / platform engineer?** Focus on Part VI (MCP, §18) and Part VII (Agents + Memory, §19 & §22). The five MCP servers are the trust boundary; the seven agents are the control plane.
- **Evaluating rigor / trust?** Read Part VIII (Evaluation + Experimentation, §20–21): the labeled benchmark, the 85%-vs-45% claim, and the experiment-design framework.
- **Hiring manager / interviewer?** Part IX (Roadmap + Narrative, §23–25) maps the maturity ladder and the resume/interview framing.

Three reading aids: (1) every term is defined once in the **Glossary** at the end of this front matter; (2) every canonical name (metric, dimension, MCP tool, agent) is enumerated in the **Canonical Reference Card** and must never be paraphrased elsewhere; (3) requirements carry stable IDs (FR-*, NFR-*) so they can be cited and traced.

---

## Table of Contents

Sections are listed in thematic reading order. Note that **Memory Architecture (22)** is presented alongside **Agent Architecture (19)** in Part VII, because memory is the state plane that the agent control plane reads from and writes to — they are best understood together rather than in strict numeric order.

| # | Section | Part |
|---|---------|------|
| **Part I — Strategy** | | |
| 1 | Product Vision | Strategy |
| 2 | Business Problem | Strategy |
| 3 | User Personas | Strategy |
| 4 | Core Product Thesis | Strategy |
| 5 | Success Metrics | Strategy |
| **Part II — Requirements** | | |
| 6 | Functional Requirements | Requirements |
| 7 | Non-Functional Requirements | Requirements |
| **Part III — Data Model** | | |
| 8 | Data Model | Data Model |
| 9 | Event Model | Data Model |
| 10 | Funnel Definitions | Data Model |
| 11 | Revenue Definitions | Data Model |
| **Part IV — Semantics** | | |
| 12 | Channel Attribution Definitions | Semantics |
| 13 | Metric Definitions | Semantics |
| 14 | Semantic Layer Design | Semantics |
| **Part V — Analytics Engineering** | | |
| 15 | Analytics Engineering Architecture | Analytics Engineering |
| 16 | dbt Project Structure | Analytics Engineering |
| 17 | BigQuery Architecture | Analytics Engineering |
| **Part VI — MCP** | | |
| 18 | MCP Architecture | MCP |
| **Part VII — Agents & Memory** | | |
| 19 | Agent Architecture | Agents |
| 22 | Memory Architecture *(presented alongside §19)* | Agents |
| **Part VIII — Evaluation & Experimentation** | | |
| 20 | Evaluation Framework | Eval / Experiment |
| 21 | Experimentation Framework | Eval / Experiment |
| **Part IX — Roadmap & Narrative** | | |
| 23 | Future Roadmap | Roadmap / Narrative |
| 24 | Interview Narrative | Roadmap / Narrative |
| 25 | Resume Narrative | Roadmap / Narrative |

---

## Document Conventions

**Naming.** All physical names — metrics, dimensions, dbt models, columns, MCP servers, MCP tools — are `snake_case` and must match the Canonical Reference Card exactly. Never invent a synonym (e.g. `conversion_pct` for `session_conversion_rate`); unknown names are a hard error at the semantic layer, not a fallback. MCP servers are named `<area>-mcp` (e.g. `warehouse-mcp`). dbt layers use fixed prefixes: `stg_<source>__<entity>` (staging), `int_<source>__<entity>` (intermediate), `fct_*` / `dim_*` (marts). Agent names are capitalized proper nouns (Orchestrator, Monitor, Decompose, Diagnose, Prescribe, Narrator, Critic).

**Code fences.** Fenced blocks are labeled by intent: `sql` for governed/dbt SQL, `python` for MCP-server or harness code, `yaml` for configuration and semantic-layer definitions, `json` for MCP request/response payloads, and `text` for diagrams, ASCII funnels, and pseudocode. SQL shown in the Bible is illustrative of the *governed* definition; at runtime the LLM never authors it — `semantic-mcp.build_query` emits it.

**Requirement numbering.** Functional requirements are `FR-<domain-letter><n>` (e.g. `FR-A1` in domain A "Data & Semantic Layer"). Non-functional requirements are `NFR-<area-letter><n>` (e.g. `NFR-P1` for Performance). Each carries a MoSCoW priority (Must / Should / Could / Won't-for-now) and a verification method. Findings, hypothesis cards, scenarios, and experiments carry their own ID prefixes (`F-*`, `H-*`, `S###`, `Exp-###`).

**Conventions for money and rates.** All money uses GA4's `_in_usd` columns; non-USD twins are never aggregated. Rates are computed as `SUM(numerator)/SUM(denominator)` after grouping (never an average of per-segment ratios) — this re-aggregation discipline is itself the defense against Simpson's paradox.

---

## Canonical Reference Card

This card is the single source of truth for shared vocabulary. It mirrors the project Foundation spec exactly. Any section that disagrees with this card is in error.

### Macro funnel stages

```text
session_start -> view_item -> add_to_cart -> begin_checkout -> add_shipping_info -> add_payment_info -> purchase
```

Helios reports **step-to-step** conversion (each stage / prior stage) AND the **overall** `session_conversion_rate = purchasing_sessions / sessions`. The funnel is session-scoped; the session key is `(user_pseudo_id, ga_session_id)`.

| # | Stage | Maps to event |
|---|-------|---------------|
| 0 | session_start | `session_start` (denominator anchor) |
| 1 | view_item | `view_item` |
| 2 | add_to_cart | `add_to_cart` |
| 3 | begin_checkout | `begin_checkout` |
| 4 | add_shipping_info | `add_shipping_info` |
| 5 | add_payment_info | `add_payment_info` |
| 6 | purchase | `purchase` |

### Canonical metric names (snake_case)

| Group | Metrics |
|-------|---------|
| Volume | `sessions`, `users`, `new_users`, `returning_users`, `engaged_sessions`, `view_item_sessions`, `add_to_cart_sessions`, `begin_checkout_sessions`, `purchasing_sessions` |
| Engagement | `engagement_rate` |
| Funnel rate | `session_conversion_rate` (= `purchasing_sessions/sessions`), `view_to_cart_rate`, `cart_to_checkout_rate`, `checkout_to_purchase_rate`, `cart_abandonment_rate`, `checkout_abandonment_rate` |
| Revenue | `transactions` (distinct `transaction_id`), `revenue` (sum `purchase_revenue_in_usd`), `gross_revenue`, `net_revenue` (gross − refunds), `aov` (= `revenue/transactions`), `items_per_transaction` |
| Efficiency | `revenue_per_session` (RPS = `revenue/sessions`), `revenue_per_user` (ARPU = `revenue/users`) |

### Canonical dimensions

`device_category`, `operating_system`, `browser`, `country`, `region`, `channel_group`, `source`, `medium`, `campaign`, `landing_page` (first `page_location` of session), `item_category`, `item_name`, `is_new_user`, `day`, `week`, `session_number_bucket`.

**Channel groups (GA4-style default grouping):** Direct, Organic Search, Paid Search, Display, Paid Social, Organic Social, Email, Affiliates, Referral, Other.

### The five MCP servers and their tools

| Server | Role | Tools |
|--------|------|-------|
| `warehouse-mcp` | Governed execution (only holder of a BigQuery client) | `list_tables`, `describe_table`, `dry_run(sql)`, `run_query(sql)`, `reconcile(metric, grain)` |
| `semantic-mcp` | The ONLY path to SQL (anti-hallucination layer) | `get_metric(name)`, `list_dimensions()`, `build_query(metric, dims, filters, window)` |
| `stats-mcp` | The ONLY path to math (determinism) | `detect_anomaly(series, method)`, `decompose_change(metric, dim, t0, t1)`, `significance_test(a, b)`, `forecast(series, horizon)`, `cohort_retention(...)`, `rfm_segment(...)` |
| `experiment-mcp` | Statistically-defensible backlog | `power_analysis(baseline, mde, alpha, power)`, `runtime_estimate(n, traffic)`, `design_experiment(hypothesis, metric)` |
| `report-mcp` | Narration and memory | `render_brief(findings)`, `save_diagnosis(...)`, `recall_prior(metric, segment)`, `export(format)` |

### The seven agents and their roles

| Agent | Model | Role |
|-------|-------|------|
| Orchestrator (Planner) | Opus | Plan the run, sequence stages, manage budget, route to Critic, finalize |
| Monitor | Sonnet | Anomaly detection over canonical metric series |
| Decompose | Sonnet | Split each anomaly into mix-shift vs rate-change vs interaction |
| Diagnose | Opus | Hypothesis-tree root-cause analysis, each branch SQL-verified |
| Prescribe | Sonnet | Convert confirmed root causes into a prioritized, powered experiment backlog |
| Narrator | Sonnet | Compose the executive Decision Brief from surviving findings |
| Critic | Opus | Adversarially refute every finding (confound, sample, seasonality, data quality) before it ships |

**Core decomposition identity** (the technical centerpiece). For an aggregate rate `R = Σ_i (w_i · r_i)` where `w_i` is segment volume share and `r_i` is segment rate, the change `ΔR` from `t0 → t1` decomposes as:

```text
mix effect    = Σ_i ( Δw_i · r_i(t0) )      # traffic composition changed
rate effect   = Σ_i ( w_i(t0) · Δr_i )      # in-segment behavior changed
interaction   = Σ_i ( Δw_i · Δr_i )         # both moved together
ΔR            = mix effect + rate effect + interaction
```

**Success-metric targets:** root-cause accuracy ≥ 85% (vs ≤ 45% naive baseline); time-to-diagnosis < 5 min/run; 0 hallucinated columns/metrics (100% governed SQL); 100% of findings carry significance + dollar impact; query cost per run under a fixed BigQuery byte budget.

**Maturity levels:** L1 Intern MVP; L2 Strong portfolio project; L3 Top-1% undergraduate project.

---

## Glossary

| Term / acronym | Definition |
|----------------|------------|
| **Action tracking** | A memory store recording whether a prescribed experiment shipped and whether the fix actually worked (status ∈ proposed / shipped / running / completed / abandoned, plus observed lift and outcome). Closes the "did-the-fix-work" loop. |
| **AOV** | Average Order Value = `revenue / transactions`. Reflects merchandise value (excludes shipping and tax). |
| **ARPU** | Average Revenue Per User = `revenue / users` (= `revenue_per_user`). Denominator is all users in the window, not just purchasers. |
| **Anomaly detection** | Deterministic flagging of abnormal movement in a metric series via `stats-mcp.detect_anomaly` (STL-residual, EWMA, or robust z-score), accounting for weekly seasonality. |
| **Channel group** | GA4-style default channel grouping (Direct, Organic Search, Paid Search, Display, Paid Social, Organic Social, Email, Affiliates, Referral, Other) derived from session-scoped source/medium. |
| **Cohort** | A set of users grouped by the week of their `user_first_touch_timestamp`; the basis for retention curves. |
| **Critic** | The adversarial verifier agent (Opus) that attempts to refute every finding before it ships; verdicts are PASS / DOWNGRADE / DROP. |
| **Decision Brief** | The primary product surface: the autonomously-produced, executive-ready artifact rendered by `report-mcp.render_brief`, where every finding carries a decomposition, a significance test, a dollar revenue-at-risk, and a recommended action. |
| **Decomposition** | Splitting an aggregate rate change `ΔR` into mix effect, rate effect, and interaction (see the core identity above); the technical centerpiece, computed by `stats-mcp.decompose_change`. |
| **DiD (difference-in-differences)** | A quasi-experimental readback: `DiD = (treated_post − treated_pre) − (control_post − control_pre)`, netting out seasonality via a comparable control segment, with parallel-trends checked on the pre-period. |
| **dry-run** | A BigQuery cost/schema check (`warehouse-mcp.dry_run`) that returns estimated scanned bytes without executing or billing; mandatory before any `run_query` to enforce the byte budget. |
| **Engaged session** | A GA4-defined engaged session (session-scoped `session_engaged = '1'`, with the GA4 fallback of engagement time / multiple page views / a conversion event); `engagement_rate = engaged_sessions / sessions`. |
| **Faithfulness** | Whether the Narrator's prose claims are entailed by the underlying SQL evidence and `stats-mcp` outputs (target ≥ 0.95); checked by rule + Critic-as-judge entailment. |
| **First-touch attribution** | Crediting a session/transaction to the channel of the user's first session ever; stored on `dim_users.first_touch_channel`. |
| **`fct_daily_funnel`** | The pre-aggregated daily funnel fact (additive step counts + revenue per day × dimension cell); the primary feed for Monitor and Decompose. |
| **`ga_session_id`** | A session id that is unique only *within* a `user_pseudo_id` (never globally); lives inside `event_params` and must be unnested. Half of the session key. |
| **Governed SQL** | SQL emitted exclusively by `semantic-mcp` from versioned metric/dimension definitions; the LLM never authors raw SQL. Guarantees 0 hallucinated columns. |
| **Grounding over generation** | The first principle: the LLM composes governed metrics and calls deterministic tools, never authoring SQL or computing statistics in token-space. |
| **Hallucination rate** | The count of columns/metrics in emitted SQL not present in the semantic registry or GA4 schema; a hard-zero CI gate. |
| **ICE / PIE** | Experiment-prioritization scores. ICE = (Impact × Confidence) / Effort; PIE = Potential × Importance × Ease. Both are deterministic and recorded on each hypothesis card. |
| **Idempotency** | Re-running a model/run over the same partitions yields byte-identical output (via partition-by-date + `insert_overwrite`); no duplicate diagnoses per window. |
| **Interaction effect** | The third decomposition term, `Σ Δw_i·Δr_i` — change attributable to weight and rate moving together. |
| **Last-touch attribution** | Crediting to the channel of the converting session itself; the Helios default for session-grained funnel and revenue diagnosis. |
| **Last-non-direct attribution** | Crediting to the most recent non-`(direct)` channel within a lookback window (GA4 default 90 days). |
| **MCP (Model Context Protocol)** | An open client-server protocol over JSON-RPC that lets the agent runtime invoke schema-typed external tools; the mechanism that makes the grounding boundary physically enforceable. |
| **MDE** | Minimum Detectable Effect — the smallest effect (often relative, e.g. 10%) an experiment is powered to detect; an input to `power_analysis`. |
| **Memory store** | Durable state across runs: diagnosis history (+ embeddings), suppression list, business glossary, seasonality/launch calendars, action tracking, and the run-state/audit trail. |
| **Mix-shift (mix effect)** | A change in an aggregate rate caused by traffic *composition* shifting between segments (weights `w_i`), with in-segment behavior unchanged. The non-causal half that naive RCA mistakes for behavior change. |
| **Quasi-experiment** | An inference design used when no live A/B traffic exists (this dataset is observational): pre/post and difference-in-differences readbacks via `stats-mcp`. |
| **Rate-change (rate effect)** | A change in an aggregate rate caused by in-segment *behavior* shifting (segment rates `r_i`), with composition held fixed. The genuinely causal half. |
| **Reconciliation** | Checking that a fact-derived metric matches `warehouse-mcp.reconcile` canonical totals within tolerance (≤ 0.5%); part of verify-then-trust. |
| **Revenue-at-risk** | The dollar counterfactual every finding carries: dollars recoverable if a degraded rate returned to its t0 / forecast baseline (≈ Δrate × affected sessions × downstream value). |
| **RFM** | Recency / Frequency / Monetary segmentation, scored into quintiles per user by `stats-mcp.rfm_segment`. |
| **RPS** | Revenue Per Session = `revenue / sessions` (= `revenue_per_session`); decomposes exactly as `session_conversion_rate × aov`. |
| **Sessionization** | Reconstructing a session row from events sharing the same `(user_pseudo_id, ga_session_id)` — GA4 ships no session row. |
| **Simpson's paradox** | When an aggregate rate moves opposite to every segment's rate because the mix shifted; the failure mode the decomposition is built to detect. |
| **Suppression list** | A memory store of acknowledged/ignored causes that must not be re-raised, with a TTL so re-emerging issues eventually re-surface. |
| **`traffic_source` gotcha** | The event-level `traffic_source` struct is USER-LEVEL first-touch attribution, not session source; Helios prefers session-scoped `event_params` source/medium and uses `traffic_source` only as a documented fallback. |
| **`user_pseudo_id`** | The device/cookie id that is the de facto user key (`user_id` is almost always NULL); cross-device stitching is therefore impossible and user-grain metrics are cookie-based approximations. |
| **Verify-then-trust** | The second principle: dry-run cost + schema validation + reconciliation + adversarial Critic before any finding ships. |
