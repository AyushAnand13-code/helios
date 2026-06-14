## 1. Product Vision

### 1.1 The 3-5 year vision

Helios is the **Autonomous Growth Diagnosis Engine**: an always-on AI Growth Analyst that does for funnel diagnosis what continuous integration did for software builds. Today a human analyst is a serial, manually-triggered, expensive root-cause oracle who is queried only when a number looks "off." In the 3-5 year horizon, Helios inverts that: diagnosis becomes a continuous, autonomous, proactive background process. Every scheduled run, Helios re-derives the full `session_start -> view_item -> add_to_cart -> begin_checkout -> add_shipping_info -> add_payment_info -> purchase` funnel, detects which steps moved, separates whether the movement came from **mix-shift** (traffic composition changed) or **rate-change** (in-segment behavior changed), prices the movement in dollars of `revenue` at risk, and ships a verified **Decision Brief** to the people who own the number — before they have to ask.

The end-state is an analytics organization where the question "why did `session_conversion_rate` drop last week?" is answered by an artifact that already exists, is statistically defensible, is grounded in governed SQL, and survived an adversarial Critic — not by a Slack message to an analyst that kicks off two days of ad-hoc querying.

### 1.2 The category Helios creates

Helios deliberately does not compete in "BI dashboards" or "ask-your-data chatbots." It creates a new category: **autonomous growth diagnosis**. The category's defining promise is *causal-style attribution of metric movement, continuously and without human prompting*, distinct from the three incumbent categories:

| Category | Primary artifact | Trigger | Answers |
|---|---|---|---|
| Descriptive BI (Looker, Tableau) | Dashboard / chart | Human pull | *What* happened |
| Conversational analytics (text-to-SQL bots) | Ad-hoc query result | Human prompt | *What* (one question at a time) |
| Product analytics (Amplitude, Mixpanel) | Funnel/retention report | Human pull | *What*, with some *who* |
| **Autonomous growth diagnosis (Helios)** | **Decision Brief** | **Scheduler (autonomous)** | ***Why*, *how much* ($), and *what to do next*** |

### 1.3 The before / after world for an analytics org

```text
BEFORE (manual root-cause analysis)
  metric dips -> someone notices (days later) -> Slack the analyst ->
  analyst context-switches -> writes ad-hoc SQL (often ungoverned) ->
  eyeballs aggregate -> misses Simpson's paradox -> ships a guess ->
  no dollar quantification -> no experiment -> decision delayed weeks

AFTER (Helios)
  scheduled run (e.g. daily) -> Monitor flags anomaly in a canonical metric ->
  Decompose splits mix vs rate vs interaction -> Diagnose builds + SQL-verifies a
  hypothesis tree -> Critic tries to refute it -> Prescribe sizes an experiment ->
  Narrator ships a Decision Brief with significance + $ revenue-at-risk + action ->
  decision made in <5 minutes of human reading time
```

### 1.4 Vision statement

> **Every material movement in the growth funnel is diagnosed automatically, priced in dollars, defended statistically, and turned into a prioritized experiment — before a human has to ask.**

### 1.5 Guiding principles

1. **Grounding over generation.** The LLM never authors raw SQL and never computes a statistic by hand. It *composes* governed metrics via `semantic-mcp` and calls deterministic tools via `stats-mcp`. This yields the 0-hallucinated-column, 100%-governed-SQL target.
2. **Verify-then-trust.** Every query is `dry_run`-cost-checked and schema-validated; every result is reconciled against canonical totals via `warehouse-mcp.reconcile`; every finding is attacked by the Critic before it ships.
3. **Determinism where it matters.** All math (decomposition, significance, power, forecasting) runs in real Python code (scipy/statsmodels/prophet), never in token-space.
4. **Every finding is actionable.** A finding without a significance test, a dollar impact, and a recommended action is not a finding.
5. **Proactive, not reactive.** Conversation is a secondary drill-down surface; the product's heartbeat is the autonomous scheduled run.

### 1.6 What success looks like at scale

At scale, Helios runs across many funnels, properties, and dimensions on a fixed BigQuery byte budget per run, produces Decision Briefs that practitioners trust without re-deriving, sustains diagnosis root-cause accuracy >=85% against a labeled benchmark (vs <=45% for a naive aggregate-only baseline), and demonstrably shortens the insight-to-action loop from weeks to a single review cycle.

## 2. Business Problem

### 2.1 The insight-to-action gap

Modern e-commerce orgs are drowning in *descriptive* signal and starving for *diagnostic* answers. Dashboards show that `session_conversion_rate` fell from 2.1% to 1.7%, but cannot say **why**, cannot say **how many dollars** that costs, and cannot say **what to do**. The gap between "we see a number moved" (insight) and "we changed the business because of it" (action) is the single most expensive inefficiency in growth analytics. Helios targets that gap directly.

### 2.2 The analyst-time cost of manual root-cause analysis

Manual root-cause analysis (RCA) of a single funnel anomaly is a multi-hour-to-multi-day serial process:

| RCA stage (manual) | Typical effort |
|---|---|
| Notice the anomaly (latency before anyone looks) | 1-5 days |
| Context-switch + reconstruct the metric definition | 0.5-1 hr |
| Write/fix ad-hoc SQL over `events_YYYYMMDD` shards | 1-3 hr |
| Slice by `device_category`, `channel_group`, `country`, ... | 1-2 hr |
| Manually reason about mix vs rate (usually skipped) | 0.5-2 hr |
| Quantify dollar impact (frequently never done) | 0.5 hr |
| Write up + socialize | 1 hr |
| **Total per anomaly** | **~1-3 analyst-days** |

Multiply by the number of metrics, segments, and weeks, and RCA consumes a large fraction of a senior analyst's time — the exact work Helios automates to a <5 min/run autonomous process.

### 2.3 The mix-shift vs rate-change failure and Simpson's paradox

The core analytical failure of naive RCA is conflating **mix-shift** with **rate-change**. For an aggregate rate `R = sum_i (w_i * r_i)` where `w_i` is segment volume share and `r_i` is segment rate, the change from `t0 -> t1` decomposes exactly into three terms:

```text
mix effect    = sum_i ( delta_w_i * r_i_at_t0 )      # composition changed
rate effect   = sum_i ( w_i_at_t0 * delta_r_i )      # behavior changed
interaction   = sum_i ( delta_w_i * delta_r_i )      # both moved together
deltaR        = mix effect + rate effect + interaction
```

A naive analyst reads only `deltaR` and attributes it to behavior. But **Simpson's paradox** means the aggregate can move in the *opposite* direction of every segment. Concretely: if `checkout_to_purchase_rate` rose in both `mobile` and `desktop`, yet aggregate `checkout_to_purchase_rate` fell because traffic mix shifted toward lower-converting `mobile`, the correct action is a *traffic/acquisition* fix, not a *checkout* fix. Naive RCA prescribes fixing checkout — wrong root cause, wasted engineering. This decomposition is Helios's technical centerpiece, executed deterministically by `stats-mcp.decompose_change`.

### 2.4 Why dashboards and descriptive analytics fail

- They report **what**, never **why**: no causal-style attribution, no mix/rate split.
- They are **pull, not push**: someone must notice and ask.
- They are **dimension-blind to interaction**: a 2-D chart cannot surface a confound across `channel_group x device_category`.
- They lack **dollar quantification**: a percentage-point drop is not a budget decision until it is `revenue`-at-risk.
- They produce **no prescription**: no experiment, no power analysis, no prioritized backlog.

### 2.5 Market context

The market validates the demand and the gap simultaneously. **Amplitude** and **Mixpanel** lead product analytics with strong funnel/retention reporting and recent "AI" features that are still fundamentally descriptive and human-triggered. A wave of **AI-analyst / text-to-SQL startups** promises "ask your data," but they are conversational (reactive), frequently hallucinate columns/metrics, and rarely carry statistical rigor or dollar impact. None of them autonomously decompose mix-vs-rate, price the movement, and ship a verified brief on a schedule. That white space — *autonomous, governed, statistically-defensible, dollar-quantified diagnosis* — is precisely Helios's category.

### 2.6 Root causes of the problem

1. **No governed semantic layer** at query time -> ad-hoc, inconsistent, hallucinated SQL.
2. **Statistics done in heads/spreadsheets** -> no significance, no decomposition, Simpson's paradox missed.
3. **Reactive triggering** -> long latency before anyone even looks.
4. **No dollar bridge** from rate movement to revenue.
5. **No adversarial check** -> first plausible story ships unrefuted.

### 2.7 Cost of inaction

Every undiagnosed week of a depressed `session_conversion_rate` or `checkout_to_purchase_rate` is recurring lost `revenue` that compounds; every misdiagnosis (wrong mix/rate call) funds the wrong fix; every delayed decision is opportunity cost in an environment where competitors iterate weekly. Inaction is not free — it is a continuously accruing, unquantified liability that Helios converts into a visible, prioritized, dollar-denominated backlog.

## 3. User Personas

### 3.1 Priya — Head of Growth (PRIMARY)

- **Role & context:** Owns the funnel and the `revenue` number; reports to the exec team weekly; manages PMs and analysts; chronically time-poor.
- **Goals:** Know *why* the funnel moved and *what to do*, fast; defend decisions with data; allocate scarce eng/experiment capacity to the highest-`revenue` opportunity.
- **Top pains:** Waits days for RCA; gets descriptive dashboards with no "why"; can't trust ad-hoc numbers; can't tell mix-shift from rate-change.
- **Jobs-to-be-done:** "When a key metric moves, tell me the root cause, the dollar impact, and the one experiment to run." "Give me a brief I can forward to the CEO."
- **How Helios serves her:** Autonomous Decision Briefs each run, each with mix/rate split, `revenue`-at-risk, significance, and a prioritized experiment backlog from `experiment-mcp`.
- **Success criteria:** Time-to-diagnosis <5 min reading; >=85% of root causes correct; every brief carries $ + significance + action.
- **Anti-needs:** Does NOT want a SQL IDE, raw tables, or a chatbot to interrogate; does NOT want ungoverned numbers.

### 3.2 Marcus — Product Manager

- **Role & context:** Owns a funnel surface (e.g., checkout: `begin_checkout -> add_shipping_info -> add_payment_info -> purchase`); ships experiments.
- **Goals:** Find where in *his* surface conversion leaks; get a testable hypothesis with expected impact and required sample size.
- **Top pains:** Doesn't know if a leak is real (significant) or noise; doesn't know if it's his surface (rate) or upstream traffic (mix); doesn't know how long a test must run.
- **Jobs-to-be-done:** "Tell me which checkout step leaks, whether it's significant, and design the experiment." "Stop me from testing a confounded mix-shift."
- **How Helios serves him:** Step-level decomposition on `cart_to_checkout_rate`/`checkout_to_purchase_rate`; `power_analysis` + `runtime_estimate` + `design_experiment` test cards.
- **Success criteria:** Experiments shipped from Helios hypotheses; reduced wasted tests on confounds.
- **Anti-needs:** Does NOT want vanity dashboards; does NOT want hand-wavy "looks lower" claims without significance.

### 3.3 Dana — Data / Product Analyst

- **Role & context:** Owns metric definitions and the dbt models; the person Slacked for every RCA.
- **Goals:** Stop being a human RCA oracle; ensure every number is governed and reconciles; do higher-order analysis.
- **Top pains:** Constant context-switching; ungoverned SQL proliferating; manually checking mix vs rate; reconciling conflicting numbers.
- **Jobs-to-be-done:** "Automate the first 80% of RCA." "Guarantee numbers come only from the governed semantic layer."
- **How Helios serves her:** `semantic-mcp` is the only SQL path; `warehouse-mcp.reconcile` validates against canonical totals; dbt facts (`fct_daily_funnel`, `fct_orders`) are the substrate she owns.
- **Success criteria:** 100% governed SQL, 0 hallucinated columns; fewer ad-hoc RCA pings; faithfulness of briefs to underlying data.
- **Anti-needs:** Does NOT want a black box she can't audit; does NOT want a tool that invents metric synonyms.

### 3.4 Elena — Founder / CEO

- **Role & context:** Reads numbers weekly; cares about `revenue`, growth trajectory, and capital efficiency; not technical in SQL.
- **Goals:** A trustworthy executive read on what's driving growth and what the team is doing about it.
- **Top pains:** Briefs that are either too shallow (a chart) or too deep (a SQL dump); no clear "so what."
- **Jobs-to-be-done:** "Give me the three things that moved `revenue`, why, and the plan."
- **How Helios serves her:** `report-mcp.render_brief` produces an exec-grade Decision Brief; `recall_prior` shows trajectory and whether prior actions worked.
- **Success criteria:** Decisions influenced; confidence in the team's diagnosis.
- **Anti-needs:** Does NOT want raw analytics tooling, jargon, or unverified speculation.

### 3.5 "The Builder" — portfolio author / hiring-target candidate

- **Role & context:** The undergraduate engineer building Helios as a top-1% portfolio project to demonstrate senior-level systems + analytics-engineering + applied-ML judgment.
- **Goals:** Show end-to-end mastery: BigQuery + dbt + MCP + Claude Agent SDK + deterministic stats + offline eval; prove the work survives adversarial scrutiny.
- **Top pains:** Portfolio projects that are demos, not systems; reviewers who doubt rigor; hand-waved "AI" with no grounding or evaluation.
- **Jobs-to-be-done:** "Build a system an engineer can rebuild from the bible years later." "Prove >=85% accuracy on a labeled benchmark with a CI eval harness."
- **How Helios serves him:** The architecture itself (seven agents, five MCP servers, governed grounding, deterministic math, adversarial Critic, GitHub Actions eval) is the demonstration.
- **Success criteria:** Hits L3 maturity; eval harness in CI; targets met; defensible against an interviewer's "how do you know?"
- **Anti-needs:** Does NOT want a toy chatbot; does NOT want unmeasured claims.

## 4. Core Product Thesis

### 4.1 The one-line thesis

An autonomous **AI Growth Analyst** that continuously diagnoses **why** the e-commerce funnel is moving, distinguishes **mix-shift from rate-change**, quantifies **revenue-at-risk in dollars**, prescribes a prioritized, statistically-defensible **experiment backlog**, and produces an executive **Decision Brief** — all grounded in governed SQL it writes, verifies, and is graded on by an offline evaluation benchmark.

### 4.2 The wedge

The wedge is one painful, high-frequency, expensive job done better than anyone: **automated mix-vs-rate root-cause diagnosis of the canonical funnel, priced in dollars.** It is narrow enough to be excellent and verifiable, and it is the exact task that incumbents (descriptive BI, conversational bots, product analytics) all leave to a human.

### 4.3 Why now

- **GA4 BigQuery export** makes event-grain data (`events_YYYYMMDD`) universally queryable.
- **dbt** makes a governed semantic/metrics layer practical.
- **Claude Agent SDK + MCP** make multi-agent plan-execute-critique orchestration with tool-grounding feasible (Opus for orchestrate/critique, Sonnet for high-volume sub-tasks).
- **Mature deterministic stats** (scipy/statsmodels/prophet/pmdarima) let math stay out of token-space.
- Together these collapse the cost of an autonomous, grounded, verifiable diagnosis engine for the first time.

### 4.4 The anti-product stance

Helios is **not** a BI dashboard, **not** an ad-hoc SQL chatbot, and **not** a generic "ask your data" tool. Conversation is a secondary drill-down surface only. The product's primary mode is autonomous and proactive: it runs on a schedule and reports without being asked.

### 4.5 The three defensibility pillars

1. **Governed-SQL grounding.** All SQL flows through `semantic-mcp` (`get_metric`, `build_query`); the LLM never authors raw SQL. Result: 100% governed SQL, 0 hallucinated columns/metrics.
2. **Deterministic statistics.** All decomposition, significance, power, and forecasting run in real code via `stats-mcp`; nothing statistical is generated by the model.
3. **Adversarial verification + offline eval.** The Critic agent tries to *refute* every finding (mix-shift confound? insufficient sample? seasonality? data quality?); a labeled benchmark in GitHub Actions CI grades root-cause accuracy (target >=85%).

### 4.6 The product loop

```text
MONITOR   (Monitor agent + stats-mcp.detect_anomaly)
   -> DECOMPOSE (Decompose agent + stats-mcp.decompose_change : mix vs rate vs interaction)
   -> DIAGNOSE  (Diagnose agent : hypothesis tree, SQL-verified via semantic+warehouse mcp)
   -> QUANTIFY  (dollarize : delta-rate -> revenue-at-risk in USD)
   -> PRESCRIBE (Prescribe agent + experiment-mcp : power_analysis, design_experiment)
   -> NARRATE   (Narrator agent + report-mcp.render_brief : the Decision Brief)
   -> LEARN     (Memory store : save_diagnosis, recall_prior, suppression list, action tracking)
                 ^----------------- feeds next MONITOR --------------------|
   (Critic agent adversarially reviews EVERY finding before NARRATE; findings must survive it)
```

### 4.7 The Decision Brief as the primary product surface

The **Decision Brief** is the product. It is the autonomously-produced, exec-ready artifact rendered by `report-mcp.render_brief`, and every finding in it carries (1) a mix/rate/interaction decomposition, (2) a significance test, (3) a dollar `revenue`-at-risk, and (4) a recommended action / experiment. The dashboard-style and conversational surfaces exist only to drill into the brief.

## 5. Success Metrics

### 5.1 North Star metric

**North Star: Verified, actioned Decision Briefs that correctly diagnose root cause** — i.e., the count (and rate) of shipped briefs whose root cause is correct, that carry $ + significance + action, and that influence a decision. It captures the whole thesis: autonomous, correct, quantified, actioned.

### 5.2 Product-quality metrics (mostly leading)

| Metric | Definition / measurement | Baseline | Target | Lead/Lag |
|---|---|---|---|---|
| Root-cause accuracy | Correct root cause on labeled benchmark in CI | <=45% (naive aggregate baseline) | >=85% | Leading |
| Decomposition error | Abs error of mix/rate/interaction vs ground truth on synthetic-labeled cases | n/a (unmeasured) | near-0 (deterministic) | Leading |
| Hallucination rate | Columns/metrics not in semantic layer per run (schema-validated) | high (ungoverned bots) | 0% (100% governed SQL) | Leading |
| Faithfulness | Brief claims reconcile to `warehouse-mcp.reconcile` canonical totals | n/a | 100% reconciled | Leading |
| Time-to-diagnosis | Wall-clock per autonomous run | ~1-3 analyst-days (manual) | <5 min/run | Leading |
| Cost per run | BigQuery bytes billed per run (dry_run-bounded) | unbounded ad-hoc | under fixed byte budget | Leading |
| Findings-with-rigor | % of findings carrying significance + $ impact | inconsistent | 100% | Leading |

### 5.3 Adoption / engagement metrics

| Metric | Measurement | Lead/Lag |
|---|---|---|
| Scheduled-run completion rate | Successful autonomous runs / scheduled runs | Leading |
| Brief open / read rate | Briefs opened by Priya/Elena / briefs shipped | Leading |
| Drill-down sessions | Secondary conversational/drill use per brief | Leading |
| Suppression-list accuracy | % anomalies correctly suppressed (no false alarms) | Leading |

### 5.4 Business-impact metrics (lagging)

| Metric | Definition / measurement | Lead/Lag |
|---|---|---|
| Dollar at-risk surfaced | Sum of `revenue`-at-risk correctly identified across briefs | Lagging |
| Experiments shipped | Experiments launched from Helios test cards (`design_experiment`) | Lagging |
| Decisions influenced | Tracked via Memory action-tracking: brief -> decision/action taken | Lagging |
| Misdiagnosis cost avoided | Wrong-fix efforts avoided by correct mix-vs-rate calls | Lagging |

### 5.5 Maturity-level success

- **L1 (Intern MVP):** loop runs end-to-end on one funnel; governed SQL; a decomposition; one brief.
- **L2 (Strong portfolio):** seven agents + five MCP servers; Critic active; CI eval harness; significance + $ on every finding.
- **L3 (Top-1% undergrad):** >=85% benchmark accuracy vs <=45% baseline; <5 min/run; 0 hallucinated columns; cost under byte budget; full autonomous scheduled operation with Memory-driven learning.
