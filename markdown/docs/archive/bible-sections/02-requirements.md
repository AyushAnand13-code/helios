## 6. Functional Requirements

This section enumerates the functional requirements (FRs) for Helios, the Autonomous Growth Diagnosis Engine, grouped by capability domain (A–K). Each FR carries a stable ID, requirement statement, rationale, acceptance criteria, and MoSCoW priority (Must / Should / Could / Won't-for-now). Every requirement is written so that an engineer can verify it deterministically against the GA4 dataset `bigquery-public-data.ga4_obfuscated_sample_ecommerce` and the five MCP servers (`warehouse-mcp`, `semantic-mcp`, `stats-mcp`, `experiment-mcp`, `report-mcp`) and seven agents (Orchestrator, Monitor, Decompose, Diagnose, Prescribe, Narrator, Critic).

### 6.A Data & Semantic Layer

| ID | Requirement | Rationale | Acceptance Criteria | Priority |
|----|-------------|-----------|---------------------|----------|
| FR-A1 | The system MUST expose every governed metric (`sessions`, `users`, `new_users`, `returning_users`, `engaged_sessions`, `engagement_rate`, `view_item_sessions`, `add_to_cart_sessions`, `begin_checkout_sessions`, `purchasing_sessions`, `session_conversion_rate`, `view_to_cart_rate`, `cart_to_checkout_rate`, `checkout_to_purchase_rate`, `cart_abandonment_rate`, `checkout_abandonment_rate`, `transactions`, `revenue`, `gross_revenue`, `net_revenue`, `aov`, `items_per_transaction`, `revenue_per_session`, `revenue_per_user`) only through `semantic-mcp.get_metric(name)`. | Anti-hallucination grounding; the LLM must never author raw metric SQL. | `get_metric(name)` returns governed SQL for all 24 canonical metrics; unknown names raise `MetricNotFound`; no agent code path emits a metric not present in the registry. | Must |
| FR-A2 | The system MUST build all SQL via `semantic-mcp.build_query(metric, dims, filters, window)`, never by string-concatenation in agent code. | Single validated SQL path; verify-then-trust. | 100% of executed queries originate from `build_query`; a static check fails CI if any agent module contains a raw `SELECT` against `events_*`. | Must |
| FR-A3 | The dbt project MUST materialize the canonical models: staging `stg_ga4__events`, `stg_ga4__event_params`; intermediate `int_ga4__sessionized`, `int_ga4__funnel_steps`; facts `fct_sessions`, `fct_funnel`, `fct_daily_funnel`, `fct_orders`, `fct_order_items`; dims `dim_users`, `dim_items`, `dim_channels`, `dim_date`; plus a semantic layer under `models/semantic`. | Reproducible, tested transformation lineage. | `dbt build` succeeds; all models exist with the exact snake_case names; `dbt docs` lineage covers source → staging → fact. | Must |
| FR-A4 | `stg_ga4__event_params` MUST unnest `event_params` into typed columns and resolve `ga_session_id` to define the session key `(user_pseudo_id, ga_session_id)`. | Sessionization is the foundation for every funnel metric. | A session row exists for each distinct `(user_pseudo_id, ga_session_id)`; null `ga_session_id` rows are quarantined and counted. | Must |
| FR-A5 | `dim_channels` MUST derive GA4 default channel grouping from SESSION-SCOPED `event_params` source/medium, falling back to user first-touch `traffic_source` only when session scope is null. | Honors the documented `traffic_source` gotcha (user-level first-touch, not session). | Channel labels ∈ {Direct, Organic Search, Paid Search, Display, Paid Social, Organic Social, Email, Affiliates, Referral, Other}; a unit test asserts fallback ordering. | Must |
| FR-A6 | `warehouse-mcp.reconcile(metric, grain)` MUST return canonical totals that every fact-derived metric is checked against. | Result reconciliation guardrail. | Every shipped finding's underlying metric matches `reconcile` within 0.5% tolerance; mismatches block the finding. | Must |
| FR-A7 | The semantic layer MUST publish `list_dimensions()` returning exactly the canonical dimensions (`device_category`, `operating_system`, `browser`, `country`, `region`, `channel_group`, `source`, `medium`, `campaign`, `landing_page`, `item_category`, `item_name`, `is_new_user`, `day`, `week`, `session_number_bucket`). | Bounded, governed slicing vocabulary. | `list_dimensions()` set-equals the canonical list; `build_query` rejects any other dimension. | Must |
| FR-A8 | The system SHOULD support an incremental dbt strategy keyed on `event_date` so only new date shards are processed per run. | Cost and runtime control on date-sharded `events_YYYYMMDD`. | Incremental run scans only shards newer than the last watermark; full-refresh remains available via flag. | Should |

### 6.B Monitoring & Anomaly Detection

| ID | Requirement | Rationale | Acceptance Criteria | Priority |
|----|-------------|-----------|---------------------|----------|
| FR-B1 | The Monitor agent MUST scan all canonical metrics over the run window for anomalies using `stats-mcp.detect_anomaly(series, method)`. | Math is deterministic and lives in code, not the LLM. | Each metric series is tested; the LLM performs no arithmetic; method ∈ {stl-residual, ewma, robust-zscore}. | Must |
| FR-B2 | Anomaly detection MUST account for weekly seasonality and the dataset window (~2020-11-01 to 2021-01-31, including Black Friday / holiday peaks). | Avoid false positives from known seasonality. | Seasonal decomposition applied before flagging; holiday spikes do not trigger spurious anomalies in the labeled benchmark. | Must |
| FR-B3 | The Monitor MUST emit, per anomaly, the metric, dimension slice, t0/t1 window, magnitude, and direction, then hand off to Decompose. | Structured handoff for plan-execute-critique. | Anomaly record validates against schema; downstream agents receive typed objects, not prose. | Must |
| FR-B4 | The system MUST consult the Memory suppression list before flagging, so previously-explained anomalies are not re-raised. | Reduce alert fatigue; learning. | A suppressed (metric, segment) pair is skipped; suppression is logged with the prior diagnosis ID. | Should |
| FR-B5 | The Monitor SHOULD rank candidate anomalies by preliminary dollar magnitude to focus the run under the time budget. | Time-to-diagnosis < 5 min/run. | Top-N anomalies by estimated `revenue` impact are processed first. | Should |

### 6.C Decomposition (Mix-Shift vs Rate-Change)

| ID | Requirement | Rationale | Acceptance Criteria | Priority |
|----|-------------|-----------|---------------------|----------|
| FR-C1 | For any aggregate rate change, the Decompose agent MUST call `stats-mcp.decompose_change(metric, dim, t0, t1)` to split ΔR into mix, rate, and interaction effects. | The technical centerpiece; resolves Simpson's paradox. | Output contains `mix_effect`, `rate_effect`, `interaction` per segment and in total; components sum to ΔR within floating tolerance 1e-6. | Must |
| FR-C2 | The decomposition MUST implement exactly: `mix = Σ Δw_i·r_i(t0)`, `rate = Σ w_i(t0)·Δr_i`, `interaction = Σ Δw_i·Δr_i`. | Determinism where it matters. | A golden-data unit test reproduces hand-computed effects; identity `Σmix+Σrate+Σinteraction = ΔR` holds. | Must |
| FR-C3 | Decomposition MUST be runnable across every canonical dimension to locate the dominant driver dimension. | Attribute the change to the right slice. | The dimension maximizing absolute contribution is reported with its segment-level breakdown. | Must |
| FR-C4 | The system SHOULD detect and flag Simpson's-paradox cases where the aggregate moves opposite to most segments. | Headline insight; defends against naive reads. | When `sign(ΔR)` differs from the majority of `sign(Δr_i)`, a paradox flag is set on the finding. | Should |

### 6.D Diagnosis / Root-Cause Analysis

| ID | Requirement | Rationale | Acceptance Criteria | Priority |
|----|-------------|-----------|---------------------|----------|
| FR-D1 | The Diagnose agent MUST build a hypothesis tree and verify each branch with governed SQL via `semantic-mcp.build_query` + `warehouse-mcp.run_query`. | Grounding over generation. | Every leaf hypothesis maps to ≥1 executed governed query; unverified branches are pruned, not reported. | Must |
| FR-D2 | Each hypothesis MUST carry a significance test from `stats-mcp.significance_test(a, b)` before promotion to a finding. | Statistical defensibility. | Findings include test statistic, p-value, and effect size; non-significant branches are discarded or marked exploratory. | Must |
| FR-D3 | Every finding MUST pass the Critic agent, which actively attempts to REFUTE it (mix-shift confound, insufficient sample, seasonality, data quality). | Adversarial verify-then-trust. | A finding ships only with a recorded Critic verdict = "survived" and the refutation attempts it withstood. | Must |
| FR-D4 | Diagnosis MUST distinguish whether a funnel movement is driven by mix-shift vs rate-change by consuming FR-C1 output, never asserting cause from aggregates alone. | Core thesis. | Each diagnosis cites the decomposition result; aggregate-only causal claims are blocked by the Critic. | Must |
| FR-D5 | The system SHOULD chain funnel steps (`session_start → view_item → add_to_cart → begin_checkout → add_shipping_info → add_payment_info → purchase`) to localize the leakiest step. | Precise root cause. | The step with the largest adverse delta in step-to-step rate is identified and reported. | Should |

### 6.E Quantification (Revenue-at-Risk)

| ID | Requirement | Rationale | Acceptance Criteria | Priority |
|----|-------------|-----------|---------------------|----------|
| FR-E1 | Every shipped finding MUST carry a dollar revenue-at-risk computed from governed `revenue`, `aov`, and affected session/conversion volumes. | "Every finding carries a dollar impact" principle. | 100% of findings include a `revenue_at_risk_usd` value derived from reconciled metrics. | Must |
| FR-E2 | Revenue-at-risk MUST be expressed as a counterfactual: dollars recoverable if the degraded rate returned to its t0 / forecast baseline. | Actionable, comparable sizing. | Computation = `Δrate × affected_sessions × downstream_value`; method is documented and reproducible. | Must |
| FR-E3 | Quantification SHOULD attach a confidence interval to the dollar estimate using the significance test inputs. | Honest uncertainty. | Findings include a low/high band on `revenue_at_risk_usd`. | Should |

### 6.F Prescription / Experimentation

| ID | Requirement | Rationale | Acceptance Criteria | Priority |
|----|-------------|-----------|---------------------|----------|
| FR-F1 | The Prescribe agent MUST produce a prioritized experiment backlog, each item from `experiment-mcp.design_experiment(hypothesis, metric)`. | Statistically-defensible action. | Backlog items are test cards with hypothesis, target metric, and design; ordered by revenue-at-risk × confidence. | Must |
| FR-F2 | Each experiment card MUST include a sample-size from `experiment-mcp.power_analysis(baseline, mde, alpha, power)` and a runtime from `runtime_estimate(n, traffic)`. | Feasibility and rigor. | Cards show required `n`, α, power, MDE, and estimated days-to-significance from actual traffic. | Must |
| FR-F3 | Prescriptions MUST tie each experiment to the specific finding and revenue-at-risk it addresses. | Traceability from diagnosis to action. | Every card references a finding ID and its `revenue_at_risk_usd`. | Must |
| FR-F4 | The system SHOULD flag experiments that are underpowered given available traffic within the dataset window. | Avoid recommending infeasible tests. | Cards where `runtime_estimate` exceeds the window are marked "insufficient traffic". | Should |

### 6.G Reporting / Decision Brief

| ID | Requirement | Rationale | Acceptance Criteria | Priority |
|----|-------------|-----------|---------------------|----------|
| FR-G1 | The Narrator agent MUST produce an executive "Decision Brief" via `report-mcp.render_brief(findings)`. | Proactive, executive-facing output. | Each run yields one brief covering top findings, each with cause, dollar impact, significance, and recommended action. | Must |
| FR-G2 | The brief MUST be generated autonomously per scheduled run, not on demand only. | Anti-product: not an ad-hoc chatbot. | A brief is rendered and persisted on every scheduled run without human prompting. | Must |
| FR-G3 | The system MUST persist briefs via `report-mcp.save_diagnosis(...)` and support `export(format)`. | Audit and distribution. | Briefs persist with run ID and timestamp; export supports at least markdown/JSON. | Must |
| FR-G4 | The brief SHOULD surface prior-run context via `report-mcp.recall_prior(metric, segment)` to show trend continuity. | Learning narrative. | Recurring issues reference the prior diagnosis and whether the prescribed action shipped. | Should |

### 6.H Memory & Learning

| ID | Requirement | Rationale | Acceptance Criteria | Priority |
|----|-------------|-----------|---------------------|----------|
| FR-H1 | The Memory store MUST persist prior diagnoses, a suppression list, the business glossary, and action-tracking. | Continuity and reduced re-work. | All four stores are queryable; each diagnosis is retrievable by (metric, segment, date). | Must |
| FR-H2 | Action-tracking MUST record whether a prescribed experiment was implemented and its observed outcome. | Closed-loop learning. | Each prescription has a status ∈ {open, shipped, won, lost, abandoned} with linkage to the post-test metric. | Should |
| FR-H3 | The business glossary SHOULD map informal stakeholder terms to canonical metric/dimension names. | Robust conversational drill-down. | A glossary lookup resolves synonyms to canonical names; misses are logged for curation. | Could |

### 6.I Evaluation

| ID | Requirement | Rationale | Acceptance Criteria | Priority |
|----|-------------|-----------|---------------------|----------|
| FR-I1 | An offline evaluation harness MUST grade root-cause diagnosis accuracy against a labeled benchmark. | Objective quality bar. | Harness reports root-cause accuracy; target ≥ 85% vs ≤ 45% naive baseline. | Must |
| FR-I2 | The harness MUST assert 0 hallucinated columns/metrics (100% governed SQL) per run. | Grounding guarantee. | Any non-governed column/metric in executed SQL fails the eval. | Must |
| FR-I3 | The harness MUST verify 100% of findings carry a significance test AND a dollar revenue-at-risk. | Enforce core principle. | Eval fails if any finding lacks either attribute. | Must |
| FR-I4 | The eval harness MUST run in CI (GitHub Actions) alongside `dbt build` + tests. | Continuous correctness. | CI is red if accuracy/grounding/coverage thresholds are not met. | Must |

### 6.J Orchestration & Scheduling

| ID | Requirement | Rationale | Acceptance Criteria | Priority |
|----|-------------|-----------|---------------------|----------|
| FR-J1 | The Orchestrator MUST run the plan-execute-critique loop across the seven agents in order: Orchestrator → Monitor → Decompose → Diagnose → Prescribe → Narrator, with Critic gating every finding. | Multi-agent control flow. | A run produces a trace showing each agent's invocation and the Critic verdict per finding. | Must |
| FR-J2 | The system MUST run autonomously on a schedule (Cloud Scheduler / cron). | Autonomous operation, not on-demand. | A scheduled trigger executes a full run end-to-end with no human input. | Must |
| FR-J3 | The Orchestrator SHOULD use Opus for orchestrate/critique and Sonnet for high-volume sub-tasks. | Cost-aware model routing. | Model assignment matches the policy and is recorded per agent call. | Should |
| FR-J4 | A run MUST fail closed: if any guardrail (reconcile, dry-run cost, Critic) fails, affected findings are withheld, not shipped. | Trust. | Withheld findings appear in the trace with the failed gate, not in the brief. | Must |

### 6.K Conversational Drill-Down (Secondary)

| ID | Requirement | Rationale | Acceptance Criteria | Priority |
|----|-------------|-----------|---------------------|----------|
| FR-K1 | The system MAY answer follow-up questions about a shipped brief, still routing all SQL through `semantic-mcp` and all math through `stats-mcp`. | Drill-down is secondary, not an ad-hoc SQL chatbot. | Conversational answers cite governed metrics only; no raw SQL is authored by the LLM. | Should |
| FR-K2 | Drill-down MUST refuse questions requiring non-governed metrics/dimensions and explain the limitation. | Bounded, grounded interface. | Out-of-vocabulary requests return a refusal referencing `list_dimensions()`/`get_metric`. | Should |
| FR-K3 | Drill-down COULD support natural-language reference to prior diagnoses via Memory. | Convenience. | "Why did this happen last week?" resolves to a stored diagnosis. | Could |

---

## 7. Non-Functional Requirements

Non-functional requirements (NFRs) define the quality attributes Helios must satisfy. Each carries an NFR-ID, a measurable target consistent with the Foundation success metrics, and a verification method.

### 7.1 Performance / Latency

| ID | Target | Verification |
|----|--------|--------------|
| NFR-P1 | Time-to-diagnosis < 5 minutes per autonomous run (end-to-end: Monitor → Narrator). | Timed CI run on the full window; p95 across runs < 5 min. |
| NFR-P2 | `warehouse-mcp.dry_run(sql)` returns cost/bytes in < 2 s; `run_query` for any single governed query returns in < 30 s on the sample dataset. | Latency assertions in integration tests. |
| NFR-P3 | Decomposition for a single dimension completes in < 1 s in `stats-mcp`. | Benchmark unit test on golden data. |

### 7.2 Cost (BigQuery Byte & LLM Token Budgets)

| ID | Target | Verification |
|----|--------|--------------|
| NFR-C1 | Total BigQuery bytes scanned per run MUST stay under a fixed byte budget; every query is gated by `dry_run` before execution. | Run aborts a query whose `dry_run` bytes exceed the per-query cap; run total is logged and asserted in CI. |
| NFR-C2 | Incremental dbt + date-shard pruning MUST avoid full-table scans of `events_*` on routine runs. | Query plan shows only required `events_YYYYMMDD` shards scanned. |
| NFR-C3 | LLM token spend per run MUST stay within a configured budget, using Opus only for orchestrate/critique and Sonnet for high-volume sub-tasks. | Per-agent token usage logged; run total asserted against budget. |

### 7.3 Reliability / Availability

| ID | Target | Verification |
|----|--------|--------------|
| NFR-R1 | A scheduled run MUST complete or fail closed with a recorded reason; no silent partial briefs. | Trace shows terminal status; partial outputs never reach `save_diagnosis` as "complete". |
| NFR-R2 | MCP tool calls MUST retry transient failures with bounded backoff (≤ 3 attempts). | Fault-injection test confirms retry then graceful failure. |
| NFR-R3 | Re-running a failed run MUST be idempotent (no duplicate diagnoses for the same window). | Duplicate-run test asserts a single persisted diagnosis per (run window, finding). |

### 7.4 Correctness & Trust Guardrails

| ID | Target | Verification |
|----|--------|--------------|
| NFR-T1 | 0 hallucinated columns/metrics — 100% of executed SQL is governed via `semantic-mcp`. | Eval harness (FR-I2) + static scan for raw `SELECT`. |
| NFR-T2 | 100% of shipped findings carry a significance test AND a dollar revenue-at-risk AND a recommended action. | Eval harness (FR-I3) gate. |
| NFR-T3 | Every metric value reconciles to `warehouse-mcp.reconcile` within 0.5%. | Reconciliation assertion per finding. |
| NFR-T4 | Every finding survives the Critic's refutation attempts before shipping. | Critic verdict recorded; "not survived" → withheld. |

### 7.5 Security & PII / Privacy

| ID | Target | Verification |
|----|--------|--------------|
| NFR-S1 | No PII egress. The dataset is obfuscated; `user_pseudo_id` is a device/cookie key only and MUST NOT be exported in briefs. | Output scan asserts no `user_pseudo_id`, raw IDs, or geo below region in exports. |
| NFR-S2 | BigQuery access MUST use least-privilege service-account credentials scoped to the public dataset and the project's transformed tables. | IAM review; no broad project-owner roles. |
| NFR-S3 | Secrets (service-account keys, LLM API keys) MUST NOT appear in logs, traces, or the repo. | Secret-scanning in CI; redaction in the logging layer. |

### 7.6 Observability (Logging, Tracing, Audit Trail)

| ID | Target | Verification |
|----|--------|--------------|
| NFR-O1 | Every run MUST emit a full audit trail: each agent call, each MCP tool call with inputs/outputs, every executed SQL, and every Critic verdict. | Trace artifact persisted per run; replayable. |
| NFR-O2 | Each finding MUST be traceable from Decision Brief → diagnosis → significance test → governed SQL → reconciled total. | Lineage walk-through on a sample finding in CI. |
| NFR-O3 | Structured logs MUST include run ID, agent name, model used, tokens, bytes scanned, and latency. | Log schema validated. |

### 7.7 Reproducibility / Determinism

| ID | Target | Verification |
|----|--------|--------------|
| NFR-D1 | All statistical computation is deterministic and lives in `stats-mcp` code, never in the LLM; identical inputs yield identical outputs. | Repeated decomposition/significance calls produce bit-stable results. |
| NFR-D2 | A pinned run (fixed dataset window, seeds, model versions) MUST reproduce the same findings set. | Two pinned runs compared; finding set is identical. |
| NFR-D3 | dbt models MUST be deterministic given the same source shards. | `dbt build` re-run yields identical fact rows. |

### 7.8 Maintainability

| ID | Target | Verification |
|----|--------|--------------|
| NFR-M1 | Adding a new governed metric MUST require only a semantic-layer definition + dbt model, no agent code change. | New-metric exercise touches only `models/semantic` and the registry. |
| NFR-M2 | All models, metrics, and dimensions MUST follow snake_case and the canonical naming. | Linter enforces names; CI fails on deviation. |
| NFR-M3 | MCP server tool signatures MUST be the exact canonical names/tools and stable across releases. | Contract tests against the five servers' tool schemas. |

### 7.9 Scalability

| ID | Target | Verification |
|----|--------|--------------|
| NFR-X1 | The pipeline MUST scale to additional date shards (extending beyond the ~2020-11 to 2021-01 window) without query-cost blowup, via incremental + partition pruning. | Synthetic shard extension stays within byte budget per run. |
| NFR-X2 | The architecture SHOULD support additional dimensions/metrics without rewriting the decomposition core. | New dimension added to `list_dimensions()` flows through `decompose_change` unchanged. |

### 7.10 Data-Quality SLAs

| ID | Target | Verification |
|----|--------|--------------|
| NFR-Q1 | dbt tests MUST enforce: unique `transaction_id` in `fct_orders`; non-null session key `(user_pseudo_id, ga_session_id)`; `session_conversion_rate ∈ [0,1]`; funnel monotonicity (`purchasing_sessions ≤ begin_checkout_sessions ≤ add_to_cart_sessions ≤ view_item_sessions ≤ sessions`). | dbt test suite green in CI. |
| NFR-Q2 | Rows with null `ga_session_id` or malformed `event_params` MUST be quarantined and counted, not silently dropped. | Quarantine table row counts reported; drop-rate threshold alarmed. |
| NFR-Q3 | `revenue` (sum `purchase_revenue_in_usd`) and `transactions` (distinct `transaction_id`) MUST reconcile to canonical totals. | `reconcile(metric, grain)` parity check. |

### 7.11 Portability

| ID | Target | Verification |
|----|--------|--------------|
| NFR-Z1 | Python MCP servers MUST run on Python 3.11 with pinned dependencies (scipy, statsmodels, prophet/pmdarima, pandas, google-cloud-bigquery). | Lockfile build reproduces the environment in CI. |
| NFR-Z2 | The system MUST run both in GitHub Actions CI and via the scheduler (Cloud Scheduler/cron) using the same containerized entrypoint. | One image runs in both contexts; no environment-specific code path. |
| NFR-Z3 | Warehouse access SHOULD be abstracted behind `warehouse-mcp` so the BigQuery backend can be swapped without changing agent logic. | Agents reference only MCP tools, never the BigQuery client directly. |
