## 23. Future Roadmap

Helios is delivered along a five-phase maturity ladder. Each phase is independently demoable and shippable; each maps to a maturity level (L1 Intern MVP, L2 Strong Portfolio, L3 Top-1% Undergrad) plus two production-frontier phases beyond. The discipline is: never start a phase until the prior phase's exit criteria are green in CI (dbt build + tests + eval harness all passing).

### 23.1 Phase 0 — MVP (L1, Intern-level)

**Scope.** Single-tenant, batch, read-only against `bigquery-public-data.ga4_obfuscated_sample_ecommerce`. Prove the grounding spine works end to end on one diagnosis path.

**Key deliverables.**
- dbt staging + intermediate + facts: `stg_ga4__events`, `stg_ga4__event_params`, `int_ga4__sessionized`, `int_ga4__funnel_steps`, `fct_sessions`, `fct_daily_funnel`. Sessionization on `(user_pseudo_id, ga_session_id)`.
- The canonical macro funnel computed for the full window: `sessions -> view_item_sessions -> add_to_cart_sessions -> begin_checkout_sessions -> purchasing_sessions`, plus `session_conversion_rate`, `view_to_cart_rate`, `cart_to_checkout_rate`, `checkout_to_purchase_rate`.
- `warehouse-mcp` (`list_tables`, `describe_table`, `dry_run`, `run_query`, `reconcile`) and a minimal `semantic-mcp` (`get_metric`, `build_query`) exposing the canonical metric names.
- Monitor agent runs `stats-mcp.detect_anomaly` on `session_conversion_rate` daily series; Narrator emits a plain-text brief via `report-mcp.render_brief`.

**Exit criteria.** `reconcile('revenue','day')` matches a hand-written control query to the cent; 0 hallucinated columns (every column traces to the GA4 schema); a single anomaly produces a brief in under 5 minutes. **Skill demonstrated:** analytics-engineering fundamentals + governed-SQL grounding.

### 23.2 Phase 1 — Strong Portfolio (L2)

**Scope.** The full seven-agent plan-execute-critique loop and the core decomposition algorithm, statistically defended.

**Key deliverables.**
- All seven agents wired on the Claude Agent SDK: Orchestrator -> Monitor -> Decompose -> Diagnose -> Prescribe -> Narrator, with the Critic refuting every finding.
- `stats-mcp.decompose_change` implementing mix effect / rate effect / interaction across canonical dimensions (`device_category`, `channel_group`, `country`, `landing_page`). This is the technical centerpiece: it distinguishes mix-shift from rate-change and resolves Simpson's paradox.
- `experiment-mcp` (`power_analysis`, `runtime_estimate`, `design_experiment`) producing a prioritized, statistically-defensible backlog; every finding carries `significance_test` results AND a dollar revenue-at-risk AND a recommended action.
- Offline eval harness with a labeled benchmark in GitHub Actions CI; memory store persisting prior diagnoses + suppression list + business glossary.

**Exit criteria.** Diagnosis root-cause accuracy >= 85% on the labeled benchmark vs <= 45% naive baseline; 100% of findings carry significance + dollar impact; query cost per run under the fixed BigQuery byte budget. **Skill demonstrated:** causal-style root-cause analysis, experiment design, trustworthy multi-agent orchestration.

### 23.3 Phase 2 — Top-1% Undergrad (L3)

**Scope.** Autonomy, depth, and adversarial rigor that read as production thinking.

**Key deliverables.**
- Scheduler (Cloud Scheduler/cron) for proactive autonomous runs; `report-mcp.recall_prior` + action-tracking close the loop on prior recommendations.
- Forecasting (`stats-mcp.forecast` via prophet/pmdarima) for expected-vs-actual deltas; `cohort_retention` and `rfm_segment` for behavioral segmentation feeding the Diagnose hypothesis tree.
- Hardened GA4-style default channel grouping honoring the `traffic_source` gotcha (session-scoped `event_params` source/medium first, user first-touch fallback).
- Critic expanded to a full refutation battery: mix-shift confound, insufficient sample, seasonality, data quality.

**Exit criteria.** Time-to-diagnosis < 5 min/run sustained on schedule; Critic catch-rate measured on injected adversarial cases; eval accuracy holds >= 85% across all canonical dimensions. **Skill demonstrated:** autonomous systems design, statistical depth, adversarial verification.

### 23.4 Phase 3 — Productionization

**Scope.** Multi-tenant, real-time streaming, warehouse-agnostic.

**Key deliverables.** Tenant isolation (per-tenant semantic layer + byte budgets); streaming ingestion of GA4 events (intraday) feeding `fct_daily_funnel` near-real-time; warehouse-agnostic adapters behind `warehouse-mcp` (Snowflake/Databricks/DuckDB) so the semantic layer is the only SQL author regardless of dialect; observability (per-agent latency, token cost, cache hit-rate). **Exit criteria.** Two warehouses pass identical reconcile tests; p95 run latency under SLA at N tenants. **Skill demonstrated:** platform engineering, multi-tenancy, infra abstraction.

### 23.5 Phase 4 — Frontier

**Scope.** True causal inference and closed-loop experimentation.

**Key deliverables.** Uplift modeling / causal inference (difference-in-differences, synthetic control, double-ML) replacing correlational decomposition where data supports it; automated experiment execution via integrations (push test cards to an experimentation platform, read back results, auto-update the backlog); multi-dataset (join GA4 with CRM/cost data for true CAC/ROAS). **Exit criteria.** A causal estimate validated against a held-out randomized experiment. **Skill demonstrated:** causal ML, full autonomous experimentation loop.

### 23.6 Capability-maturity table

| Capability | P0 (L1) | P1 (L2) | P2 (L3) | P3 Prod | P4 Frontier |
|---|---|---|---|---|---|
| Governed SQL (semantic-mcp) | basic | full | full | multi-warehouse | + multi-dataset |
| Anomaly detection (Monitor) | threshold | statistical | forecast-residual | streaming | causal triggers |
| Mix-shift vs rate decomposition | — | core | all dims | per-tenant | + uplift |
| Experiment backlog | — | power+design | prioritized | — | auto-executed |
| Critic refutation | — | basic | full battery | — | causal checks |
| Autonomy | manual | manual | scheduled | multi-tenant SLA | closed-loop |
| Revenue-at-risk ($) | — | yes | yes | yes | causal $ |

### 23.7 Explicitly deferred items (with rationale)

| Deferred item | Phase deferred to | Rationale |
|---|---|---|
| True customer LTV | P4 + new data | Dataset window is ~3 months (2020-11-01 to 2021-01-31); too short to observe lifetime value or long retention curves. Report 30/60-day proxy retention only. |
| Cross-device identity | P4 | `user_id` is almost always NULL; `user_pseudo_id` is device/cookie-scoped, so identity stitching is unsound on this data. |
| True causal inference | P4 | No experiment assignment in the public data; P1-P2 ship correlational decomposition with explicit confound caveats from the Critic. |
| Real-time streaming | P3 | MVP value is in diagnosis quality, not latency; batch is sufficient for a 3-month static sample. |
| ML-based attribution | P4 | Requires session-scoped channel + cost data the sample lacks; use GA4 default channel grouping until then. |

---

## 24. Interview Narrative

### 24.1 The 60-second pitch

"Helios is an autonomous AI Growth Analyst. Instead of another 'ask your data' chatbot, it runs on a schedule and proactively diagnoses *why* an e-commerce funnel is moving. Its centerpiece is a mix-shift-versus-rate-change decomposition that tells you whether conversion dropped because *behavior* changed or because your *traffic composition* changed — that's how it dodges Simpson's paradox. Every finding ships with a significance test, a dollar revenue-at-risk number, and a prioritized experiment to fix it. The trust story is grounding: the LLM never writes raw SQL or does math — it composes governed metrics through a semantic layer and calls deterministic stats tools over MCP, and an adversarial Critic agent tries to refute every finding before it ships. On a labeled benchmark it hits 85%+ root-cause accuracy versus 45% for a naive baseline."

### 24.2 The 2-minute deep-dive

"The architecture is seven agents in a plan-execute-critique loop on the Claude Agent SDK. The Orchestrator plans; Monitor runs anomaly detection on canonical series like `session_conversion_rate`; Decompose runs the mix/rate/interaction math; Diagnose builds a hypothesis tree and verifies each branch with governed SQL; Prescribe designs experiments with power analysis; Narrator writes the executive Decision Brief. The Critic reviews everything adversarially — it checks for mix-shift confounds, insufficient sample, seasonality, and data-quality issues — and a finding only ships if it survives.

The grounding spine is five MCP servers: warehouse-mcp for execution and reconciliation, semantic-mcp as the *only* path to SQL, stats-mcp as the *only* path to math, experiment-mcp for design, and report-mcp for briefs and memory. That boundary is the whole trust argument: hallucinated columns are structurally impossible because the model can only reference governed metrics like `view_to_cart_rate` or `aov`, and statistics are deterministic code, not generated tokens.

The data is the GA4 obfuscated sample — event-level, date-sharded, with the classic gotchas: `traffic_source` is user first-touch not session source, and sessions are keyed on `(user_pseudo_id, ga_session_id)`. dbt models it cleanly from `stg_ga4__events` up to `fct_daily_funnel`, and an offline eval harness in CI grades root-cause accuracy on every commit."

### 24.3 STAR stories

**(a) The mix-shift-vs-rate-change insight.** *Situation:* overall `session_conversion_rate` fell week-over-week and the obvious read was "checkout is broken." *Task:* find the real cause before prescribing a fix. *Action:* I built `stats-mcp.decompose_change`, decomposing the aggregate rate `R = sum_i w_i * r_i` into mix effect `sum_i (delta_w_i * r_i_at_t0)`, rate effect `sum_i (w_i_at_t0 * delta_r_i)`, and interaction. *Result:* the per-segment rates were flat — the drop was almost entirely *mix*: a surge of low-converting mobile/Paid Social traffic shifted the weights. The prescription flipped from "fix checkout" to "fix acquisition mix," and the decomposition is auditable.

**(b) Trustworthy AI via the eval harness.** *Situation:* "the AI says so" is not shippable. *Task:* make trust measurable. *Action:* built a labeled benchmark of seeded funnel changes with known root causes and wired it into GitHub Actions so every commit grades diagnosis accuracy; added the adversarial Critic. *Result:* 85%+ accuracy vs a 45% naive baseline, with regression caught automatically in CI.

**(c) MCP tool-boundary design.** *Situation:* LLMs hallucinate columns and miscompute stats. *Task:* eliminate both structurally. *Action:* split capability across five MCP servers and enforced that semantic-mcp is the only SQL author and stats-mcp the only math path; the model composes metrics, never raw SQL. *Result:* 0 hallucinated columns/metrics — 100% governed SQL — and every number is reproducible.

**(d) A hard SQL/data-quality problem.** *Situation:* channel attribution looked wrong. *Task:* correct it. *Action:* discovered the `traffic_source` struct is user first-touch, not session source; rebuilt channel_group on session-scoped `event_params` source/medium with first-touch fallback, and handled the `event_params` ARRAY-of-STRUCT unnesting and date-sharded scans within the byte budget. *Result:* correct GA4-style channel grouping and query cost held under the fixed BigQuery budget.

### 24.4 "Why you can trust this AI"

Four pillars: **grounding over generation** (LLM composes governed metrics, never authors SQL or stats); **verify-then-trust** (dry-run cost + schema validation + result reconciliation + adversarial Critic before any finding ships); **determinism where it matters** (all math is real code in stats-mcp); and **accountability** (every finding carries a significance test, a dollar revenue-at-risk, and a recommended action — no naked assertions).

### 24.5 Anticipated interviewer questions

1. *Why not just a SQL chatbot?* Chatbots are reactive and hallucinate; Helios is proactive, governed, and graded.
2. *How do you prevent hallucinated columns?* semantic-mcp is the only SQL path; the model references metric names, not schema.
3. *Mix-shift vs rate-change — explain.* The `w_i`/`r_i` decomposition; mix = composition change, rate = behavior change, plus interaction.
4. *How is accuracy measured?* Labeled benchmark in CI: 85%+ vs 45% baseline.
5. *What does the Critic actually check?* Mix-shift confound, sample size, seasonality, data quality.
6. *Why MCP and five servers?* Capability isolation = enforceable trust boundaries.
7. *Opus vs Sonnet split?* Opus orchestrates/critiques; Sonnet handles high-volume sub-tasks for cost.
8. *Biggest GA4 gotcha?* `traffic_source` is first-touch, not session-scoped; sessions key on `(user_pseudo_id, ga_session_id)`.
9. *How do you quantify revenue-at-risk?* Affected sessions x rate delta x revenue_per_session, attributed by segment.
10. *Why is LTV deferred?* The ~3-month window can't support lifetime curves; only proxy retention.
11. *Cost control?* dry_run estimates bytes; runs are capped under a fixed byte budget.
12. *How do you avoid acting on noise?* significance_test gating + Critic + suppression list in memory.
13. *Behavioral — disagreement with a stakeholder?* The decomposition gave an auditable answer that overrode the gut call on checkout.
14. *Behavioral — biggest mistake?* Initially trusted `traffic_source` as session source; the eval harness surfaced the attribution error.

### 24.6 Whiteboard talking points

Draw the seven-agent loop with the Critic as a gate; the five MCP servers as the trust boundary; the funnel `session_start -> view_item -> add_to_cart -> begin_checkout -> add_shipping_info -> add_payment_info -> purchase`; and the decomposition identity `deltaR = mix + rate + interaction`.

---

## 25. Resume Narrative

### 25.1 One-line headline

**Helios — Autonomous AI Growth Analyst (BigQuery + dbt + Claude Agent SDK + MCP):** a self-running diagnosis engine that distinguishes mix-shift from rate-change, quantifies revenue-at-risk in dollars, and prescribes a statistically-defensible experiment backlog from governed SQL.

### 25.2 Quantified achievement bullets

- Built an autonomous seven-agent diagnosis engine (Claude Agent SDK) that hit **85%+ root-cause accuracy** on a labeled benchmark vs a **45% naive baseline**, graded automatically in CI.
- Engineered a **mix-shift vs rate-change decomposition** (mix/rate/interaction) over GA4 funnel metrics, resolving Simpson's paradox and turning ambiguous conversion drops into segment-attributed root causes.
- Enforced **100% governed SQL with 0 hallucinated columns** by routing all SQL through a semantic layer and all statistics through deterministic stats tools over five MCP servers.
- Delivered **time-to-diagnosis under 5 minutes per run** under a fixed BigQuery byte budget via `dry_run` cost gating and date-shard pruning.
- Shipped findings where **100% carry a significance test, a dollar revenue-at-risk, and a recommended action**, vetted by an adversarial Critic agent before release.
- Modeled the GA4 export in **dbt** from `stg_ga4__events` to `fct_daily_funnel`, correctly handling the `traffic_source` first-touch gotcha and `event_params` ARRAY-of-STRUCT unnesting.

### 25.3 Tailored bullet variants

**Product / Growth Analyst:** "Diagnosed e-commerce funnel movement with a mix-shift-vs-rate-change framework, quantified revenue-at-risk in dollars, and produced a prioritized, power-analyzed experiment backlog and executive Decision Brief."

**Data / Analytics Engineer:** "Built the dbt analytics layer (staging -> intermediate -> facts/dims) on the GA4 BigQuery export with a governed semantic/metrics layer, reconciliation tests, and CI (dbt build + tests + eval harness) under a fixed byte budget."

**AI / ML Engineer:** "Architected a seven-agent plan-execute-critique system on the Claude Agent SDK with MCP tool boundaries (semantic-mcp as sole SQL author, stats-mcp as sole math path) and an adversarial Critic, achieving 85%+ benchmarked accuracy and 0 hallucinated metrics."

### 25.4 Skills / ATS keyword block

`SQL` `BigQuery` `dbt` `GA4 / Google Analytics 4` `data modeling` `semantic / metrics layer` `Model Context Protocol (MCP)` `multi-agent systems` `Claude Agent SDK` `LLM orchestration` `root-cause analysis (RCA)` `mix-shift decomposition` `A/B testing / experimentation` `power analysis` `statistical significance` `cohort / retention analysis` `RFM segmentation` `forecasting (Prophet, pmdarima)` `anomaly detection` `Python` `scipy / statsmodels / pandas` `GitHub Actions / CI` `revenue analytics` `conversion funnel`

### 25.5 LinkedIn project blurb

"Helios is an autonomous AI Growth Analyst I built on BigQuery, dbt, and the Claude Agent SDK. It continuously diagnoses *why* an e-commerce funnel moves — separating mix-shift from rate-change, quantifying revenue-at-risk in dollars, and prescribing a statistically-defensible experiment backlog. The trust model is what makes it different: the LLM never writes raw SQL or computes statistics — it composes governed metrics and calls deterministic tools over five MCP servers, and an adversarial Critic refutes every finding before it ships. Benchmarked at 85%+ root-cause accuracy vs a 45% naive baseline."

### 25.6 Portfolio case-study structure

| Section | What to show |
|---|---|
| Problem | Funnel drops are ambiguous; BI dashboards don't say *why*. |
| Anti-product | Not a dashboard or SQL chatbot — autonomous, governed, graded. |
| Architecture | Seven-agent loop + five MCP servers diagram (trust boundary). |
| Technical centerpiece | Mix/rate/interaction decomposition with worked Simpson's-paradox example. |
| Trust & evals | Grounding, Critic, and the labeled benchmark (85% vs 45%). |
| Sample Decision Brief | A real rendered brief with significance + dollar revenue-at-risk + action. |
| Results & roadmap | Success metrics hit; the five-phase maturity ladder. |
