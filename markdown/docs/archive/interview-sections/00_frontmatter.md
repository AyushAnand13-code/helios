# Helios - Interview Guide

**Autonomous Growth Diagnosis Engine - the definitive prep**

This guide is the single source of truth for defending Helios in placement interviews for Product, Growth, Data, Business, Analytics-Engineering, and AI/Data-Engineering roles. It pairs the concepts an interviewer probes with the exact Helios decision that proves you have done the work - so every answer moves from a general principle to concrete, quantified evidence.

---

## How to use this guide

**Study order.** Read the Fact Sheet below until you can reproduce it on a whiteboard from memory - the decomposition identity, the eval numbers, and the three pillars are non-negotiable. Then work the sections in order: the early sections build the problem framing and architecture mental model; the middle sections drill the technical centerpiece (mix-shift vs rate-change), the statistics, and the trust story; the later sections cover honesty/limitations, role positioning, and rapid-fire rebuttals. Skim everything once end-to-end before deep-drilling, so you can cross-reference.

**How to drill the Q&A.** Each Q&A is built as: (a) the concept stated generally, (b) the tradeoff and the failure mode it avoids, (c) the "Why Helios demonstrates it" tie-back to a specific named component. Do not memorize answers verbatim - internalize the *structure* so you can recombine pieces when a question comes in a shape you did not rehearse. For every question, force yourself to name a number, name an alternative you rejected, and name the component.

**The rehearse-out-loud rule.** Reading is not rehearsing. Say every answer aloud, end to end, under 90 seconds, before you consider it learned. If you cannot say it without filler or without inventing a number, you do not know it yet. Record yourself once per section; an answer you cannot deliver fluently out loud will collapse under follow-up pressure.

---

## Table of Contents

1. The Problem and the Insight-to-Action Gap
2. What Helios Is (and Is Not)
3. System Architecture and the MCP Server Design
4. The Agent State Machine and Orchestration
5. The Technical Centerpiece - Mix-Shift vs Rate-Change Decomposition
6. The Semantic Layer and Governed SQL
7. The Data Model (dbt, GA4, Sessionization)
8. Statistics, Forecasting, and Experiment Design
9. The Critic, Adversarial Verification, and the Offline Benchmark
10. Memory and the Did-the-Fix-Work Loop
11. Honesty, Limitations, and Senior Judgment
12. Role-Specific Positioning and Behavioral Framing
13. Rapid-Fire Rebuttals and Hard Follow-Ups

---

## The Helios Fact Sheet (memorize this)

**One-line thesis.** Helios is an always-on AI Growth Analyst that diagnoses *why* an e-commerce funnel moved, quantifies revenue-at-risk in dollars, and ships a prioritized, statistically-defensible experiment backlog - all grounded in governed SQL it never hand-authors.

**The problem in one line.** Dashboards report *what* happened, not *why*; manual root-cause takes ~1-3 analyst-days per anomaly, routinely confuses mix-shift with rate-change, and rarely carries dollar impact or a prescribed experiment.

**The architecture in 5 lines:**

| Layer | What it is |
|---|---|
| 5 MCP servers | warehouse-mcp (sole BigQuery client; dry_run -> run_query byte gate; reconcile <=0.5%), semantic-mcp (ONLY SQL path; build_query from governed registry), stats-mcp (ONLY math path), experiment-mcp (power/runtime/design), report-mcp (render_brief + memory) |
| 7 agents | Orchestrator (Opus), Monitor (Sonnet), Decompose (Sonnet), Diagnose (Opus), Critic (Opus), Prescribe (Sonnet), Narrator (Sonnet) - on a deterministic FSM; LLM composes tool calls, never controls flow |
| Semantic layer | semantic_models.yml: 28 metrics + 16 dimensions, referential-integrity compiled, maps 1:1 to dbt MetricFlow - single source of truth for all SQL |
| Memory | BigQuery helios_memory + vector store: diagnosis history (embeddings), suppression list, seasonality/launch calendars, action-tracking loop |
| Evaluation | Offline labeled benchmark: synthetic anomalies injected into a frozen GA4 copy; the pipeline must rediscover them |

**The decomposition identity (write it cold):**

> deltaR = **mix** + **rate** + **interaction**
> where R = sum_i (w_i * r_i),  mix = sum_i (dw_i * r_i(t0)),  rate = sum_i (w_i(t0) * dr_i),  interaction = sum_i (dw_i * dr_i)
> (w = segment volume share, r = segment rate). Computed deterministically by stats-mcp.decompose_change. Drill rate-effects (real behavior) before mix-effects (composition artifacts) - this dissolves Simpson's paradox.

**Numbers to never forget:**

| Metric | Value |
|---|---|
| Root-cause segment accuracy | **>=85%** vs **<=45%** naive baseline |
| Hallucinated columns | **0** |
| Decomposition MAPE | **<=10%** |
| Runtime | **<5 min/run** |
| BigQuery budget | **5 GiB** fixed |
| Labeled scenarios | **50** across 7 buckets |
| Semantic registry | **28 metrics / 16 dimensions** |
| Reconciliation tolerance | **<=0.5%** |

**The three defensibility pillars:** (1) **governed-SQL grounding** - semantic-mcp is the only SQL path (0 hallucinated columns); (2) **deterministic statistics** - stats-mcp is the only math path; (3) **adversarial verification + offline eval** - the Critic plus the 85%-vs-45% benchmark. Thesis: the hard part is not generating insights, it is making them *correct and trusted*.

**The four honesty points:** (1) dataset is **observational & historical** (Nov 2020-Jan 2021), so Helios *designs and sizes* experiments and runs quasi-experimental readbacks (pre/post, diff-in-diff) - it does not run live A/Bs; (2) **~3-month window** -> true LTV deferred, report short-horizon proxies with stated assumptions; (3) **user_id almost always null** -> identity is cookie-grain (user_pseudo_id), user-level metrics are approximations; (4) **traffic_source gotcha** -> event-level source is user FIRST-TOUCH not session source, so Helios derives session-scoped source/medium and falls back to first-touch.

**The canonical funnel:** session_start -> view_item -> add_to_cart -> begin_checkout -> add_shipping_info -> add_payment_info -> purchase. Revenue = purchase_revenue_in_usd. Session = (user_pseudo_id, ga_session_id). Dataset = bigquery-public-data.ga4_obfuscated_sample_ecommerce.

**The 10 GA4 channel groups:** Direct, Organic Search, Paid Search, Display, Paid Social, Organic Social, Email, Affiliates, Referral, Other.

---

## One-sentence positioning per role

- **Product Analyst:** "I built a system that goes past *what* a funnel did to *why* it moved - decomposing each conversion-step drop into mix vs rate, attaching dollar revenue-at-risk, and prescribing the experiment to fix it."
- **Growth Analyst:** "Helios turns an anomaly into a prioritized, power-sized experiment backlog with quantified upside, so growth bets are ranked by defensible impact rather than by whoever argues loudest."
- **Data Analyst:** "I automated the 1-3-day root-cause grind into a <5-minute run that never hallucinates a column, because every query is composed from a governed 28-metric semantic registry and reconciled to <=0.5%."
- **Analytics Engineer:** "I built a GA4 -> dbt warehouse - staging, sessionized intermediate, monotonic funnel flags, marts - with a semantic layer mapping 1:1 to MetricFlow as the single source of truth for every downstream metric."
- **AI/Data Engineer:** "I orchestrated 7 Claude agents on a deterministic finite-state machine over 5 MCP servers, where the LLM only composes governed tool calls and never controls flow or authors SQL - LLM judgment, deterministic guarantees."
- **Founder/Consulting:** "I shipped an autonomous analyst that closes the insight-to-action gap end-to-end - diagnosis, dollar impact, prescription, and an executive Decision Brief - and proved it on a 50-scenario labeled benchmark, not a demo."

---

## Answer voice reminder

Three rules govern every answer in this guide - obey them out loud, not just on paper:

1. **Concept first, then Helios.** Explain the general principle and why it matters *before* citing Helios. Never talk only about the project - show you understand the idea independently, then use Helios as the concrete proof.
2. **Quantify + tradeoff + honesty.** State a number, name the alternative you rejected and the tradeoff, and surface the relevant limitation. Honesty about constraints (observational data, cookie-grain identity, 3-month window) reads as senior judgment, not weakness.
3. **Tie to a specific component.** Close with a "Why Helios demonstrates it" line that names the exact server, agent, or artifact - semantic-mcp, the Critic, decompose_change, semantic_models.yml - using canonical names accurately. Tight, high-signal prose; no buzzword soup.
