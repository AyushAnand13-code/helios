# Helios — Artifact Dependency Map & Build Order

**Companion to:** `HELIOS_PROJECT_BIBLE.md` · **Version:** v1.0 · **Date:** 2026-06-03

**Purpose.** This document is the build-time complement to the Bible. The Bible says *what* every artifact is; this map says *what must exist before each artifact can be built*, *in what order to build them*, *which artifacts are load-bearing*, and *what to build first*. It is optimized for **long-term project continuity**: an engineer returning years later (or an AI agent resuming the build) should be able to read this map plus the Bible and reconstruct Helios in dependency-safe order without rediscovering the graph.

Every artifact below traces to a Bible section (cited as §). The only artifact that currently exists is the Bible itself and this map; everything else is "remaining."

---

## 0. Legend & conventions

- **Tier (T0–T13):** topological layers. An artifact may only depend on its own tier or lower tiers. No back-edges = acyclic by construction.
- **`depends on`:** *direct* upstream artifacts (transitive deps omitted for readability).
- **★ Keystone:** load-bearing artifact — many things break or are wrong if this is wrong. Build with the most care and the most tests.
- **∥ Parallelizable:** sits on an independent subgraph and can be built concurrently with the main data spine.
- **Maturity tag:** `[P0]` MVP/L1, `[P1]` Strong Portfolio/L2, `[P2]` Top-1%/L3, `[P3/P4]` production/frontier (§23).

---

## 1. Full artifact inventory (tiered, with direct dependencies)

### T0 — Repository & environment foundation `[P0]`
| ID | Artifact | Depends on | Bible | Notes |
|----|----------|-----------|-------|-------|
| A0.1 | Repo scaffold (`pyproject.toml`/`requirements.txt`, `.gitignore`, package layout `helios/`) | — | §16.1 | Python 3.11; deps: google-cloud-bigquery, scipy, statsmodels, prophet/pmdarima, mcp, anthropic. |
| A0.2 | **CLAUDE.md** ★ | Bible | §12 (workflows) | Continuity anchor for AI-assisted dev: canonical names, grounding rules G1–G5, dbt conventions. |
| A0.3 | GCP project + service account + IAM (`bigquery.dataViewer`, `bigquery.jobUser`) + ADC | — | §17, §18.3 | Read-only on `bigquery-public-data`. Prereq for any query. |
| A0.4 | `dbt_project.yml`, `profiles.yml`, `packages.yml` | A0.1, A0.3 | §16.7–16.8 | Materializations, partition/cluster config; targets `helios_dev`/`helios_prod`. |
| A0.5 | `mcp_servers.yaml` (stub → finalized) | A0.1 | §18.10 | Stub at T0; finalize per server as built (T6). |

### T1 — dbt sources, macros, seeds `[P0]` (depends: T0)
| ID | Artifact | Depends on | Bible | Notes |
|----|----------|-----------|-------|-------|
| A1.1 | `macros/get_event_param.sql` | A0.4 | §16.6 | Typed `event_params` extraction; used by all staging. |
| A1.2 | `macros/sessionize.sql` | A1.1 | §16.6 | Builds `(user_pseudo_id, ga_session_id)` key. |
| A1.3 | `macros/channel_group.sql` (`channel_group_case()`) ★ | A0.4 | §16.6 / §12.5 | **Single source of truth** for the 10 channel groups. |
| A1.4 | `macros/test_revenue_reconciles.sql` (custom generic test) | A0.4 | §16.5 | Underpins reconciliation guarantee. |
| A1.5 | `seeds/channel_group_mapping.csv` | A0.4 | §16.1 | source/medium → channel_group seed. |
| A1.6 | `models/staging/src_ga4.yml` (source decl + freshness) | A0.4 | §16.3 | Declares `events_*` shards. |

### T2 — Staging models `[P0]` (depends: T1)
| ID | Artifact | Depends on | Bible | Notes |
|----|----------|-----------|-------|-------|
| A2.1 | `stg_ga4__events.sql` | A1.1, A1.2, A1.6 | §16.9 | 1:1 typed/renamed events; surfaces session_key, source/medium, revenue. |
| A2.2 | `stg_ga4__event_params.sql` | A1.6 | §8.1 | Unnested long key/value table. |
| A2.3 | `stg_ga4__schema.yml` (tests + docs) | A2.1, A2.2 | §16.1 | not_null/unique on keys. |

### T3 — Intermediate models `[P0]` — THE DATA KEYSTONE (depends: T2)
| ID | Artifact | Depends on | Bible | Notes |
|----|----------|-----------|-------|-------|
| A3.1 | `int_ga4__sessionized.sql` ★ | A2.1, A2.2, A1.2, A1.3 | §8.5 | Session row, `landing_page`, session-scoped source/medium (traffic_source gotcha), engagement. **If wrong, every metric is wrong.** |
| A3.2 | `int_ga4__funnel_steps.sql` ★ | A2.1, A3.1 | §10, §8.3 | `reached_*` max-downstream monotonic flags. Drives the whole funnel. |
| A3.3 | `int_ga4__schema.yml` | A3.1, A3.2 | §16.1 | Funnel-monotonicity & uniqueness tests. |

### T4 — Marts (facts + dims) `[P0/P1]` (depends: T3)
| ID | Artifact | Depends on | Bible | Notes |
|----|----------|-----------|-------|-------|
| A4.1 | `dim_date.sql` ∥ | A0.4 | §8.4 | Date spine 2020-11-01..2021-01-31; near-independent. |
| A4.2 | `dim_channels.sql` | A1.3, A1.5 | §8.4 | 10 channel groups; PK channel_group. |
| A4.3 | `dim_users.sql` | A3.1 | §8.4 / §8.6 | First-touch attrs; cookie-grain identity. |
| A4.4 | `dim_items.sql` ∥ | A2.1 | §8.4 | Item/category catalog from items[]. |
| A4.5 | `fct_sessions.sql` | A3.1, A4.2 | §8.3 | Session attributes/engagement. |
| A4.6 | `fct_funnel.sql` ★ | A3.1, A3.2 | §8.3 | One row/session + `reached_*` + session_revenue. Grain-defining session fact. |
| A4.7 | `fct_daily_funnel.sql` ★ | A4.6 | §8.3 / §16.10 | Daily × dimension counts incl. `revenue`. **Primary feed for Monitor + Decompose + eval injector.** Pinned to aggregate `fct_funnel` (A4.6), which carries `session_revenue`; the §16.10 sample reading from `int_ga4__funnel_steps` is an abbreviated illustration (counts only, no revenue). |
| A4.8 | `fct_orders.sql` ∥ | A2.1 | §8.3 | One row/transaction; revenue/gross/net/aov inputs. |
| A4.9 | `fct_order_items.sql` ∥ | A2.1, A4.8, A4.4 | §8.3 | Exploded items[]. |
| A4.10 | `fct_funnel_by_dim.sql` | A4.6, A4.1–A4.2 | §16.2 | Decomposition input (mix vs rate). |
| A4.11 | `fct_cohorts.sql` | A4.3, A4.8 | §16.2 | Retention input for `cohort_retention`. `[P2]` |
| A4.12 | `core__/finance__/growth__schema.yml` schema tests, `snapshots/snap_dim_items.sql` | A4.1–A4.11 | §16.1, §16.4 | Generic tests incl. `accepted_values` on channel_group, `revenue_reconciles`. (Singular test = A4.14.) |
| A4.13 | `exposures/exposures.yml` | A4.* (finalize after T8 — scheduled in M9) | §16.1 | Declares agents + Decision Brief as consumers; lineage. |
| A4.14 | `tests/assert_session_conversion_rate_bounds.sql` (singular data test) | A4.7 | §16.1, §15.4 | Asserts `session_conversion_rate` ∈ [0,1] and funnel-rate bounds, computed inline from `fct_daily_funnel` counts (no semantic-layer dep). Runs in CI. |

### T5 — Semantic layer `[P0/P1]` — THE GOVERNANCE KEYSTONE (depends: T4)
| ID | Artifact | Depends on | Bible | Notes |
|----|----------|-----------|-------|-------|
| A5.1 | `models/semantic/semantic_layer.yaml` (metric + dimension registry) ★★ | A4.6, A4.7, A4.8 | §14.1–14.3 | The single source of truth for all governed SQL. Everything that queries goes through this. |
| A5.2 | `metrics__schema.yml` + referential-integrity compile check | A5.1 | §14.4–14.5 | Dangling-reference = hard fail; versioned. |

### T6 — MCP servers `[P0→P2]` (depends: T5, T4, T0; report-mcp depends on T7)
| ID | Artifact | Depends on | Bible | Notes |
|----|----------|-----------|-------|-------|
| A6.0 | MCP shared scaffolding (FastMCP base, JSON-RPC, schemas) | A0.1 | §18.3, §18.12 | Common server harness. |
| A6.1 | **`warehouse-mcp`** ★ | A6.0, A0.3, A4.* | §18.4, §18.12 | Sole BigQuery client; `dry_run`→`run_query` byte-budget gate; `reconcile`. |
| A6.2 | **`semantic-mcp`** ★ | A6.0, A5.1 | §18.5, §14.4 | The ONLY path to SQL; `build_query` chokepoint. Output feeds A6.1. |
| A6.3 | **`stats-mcp`** ★ ∥ | A6.0 | §18.6 | The ONLY path to math. `decompose_change` = thesis centerpiece. Data-independent → build early in parallel. |
| A6.4 | `experiment-mcp` ∥ | A6.0 | §18.7 | power/runtime/design; no data access. `[P1]` |
| A6.5 | `report-mcp` core (`render_brief`, `export`) ∥ | A6.0 | §18.8 | Stateless rendering/export; **no memory dependency** → buildable at P0. Memory-backed tools are split out to A7.4. |

### T7 — Memory store `[P1/P2]` (depends: T0; gates report-mcp + Critic)
| ID | Artifact | Depends on | Bible | Notes |
|----|----------|-----------|-------|-------|
| A7.1 | `helios_memory` DDL (diagnosis_history, suppression_list, glossary, seasonality_calendar, launch_calendar, action_tracking, run_state, audit_log) ★ | A0.3 | §22.1–22.5 | Durable system of record. |
| A7.2 | Vector store setup (embeddings of findings) | A7.1 | §22.1 | ANN recall for `recall_prior`. |
| A7.3 | Memory seeds (glossary; seasonality: Black Friday 2020 / Dec peak / Jan trough; launch_calendar) ∥ | A7.1 | §22.3 | Confound priors the Critic needs. |
| A7.4 | `report-mcp` memory tools (`save_diagnosis`, `recall_prior` + vector upsert) ★ | A6.5, A7.1, A7.2 | §18.8, §22.1 | The stateful half of report-mcp; the sole memory-I/O path for agents (resolves the vector store's writer/reader). Depends on lower-tier A6.5 + same-tier A7.1/A7.2 — no back-edge. |

### T8 — Agents (Claude Agent SDK) `[P0→P2]` (depends: T6 + T7)
| ID | Artifact | Depends on | Bible | Notes |
|----|----------|-----------|-------|-------|
| A8.0 | Agent framework: control plane / FSM, typed JSON envelope, per-agent allow-lists, context windowing, retries ★ | A6.0–A6.3, A6.5 | §18.9, §19.2, §19.5 | Shared substrate. Scoped to the MCP servers the minimal loop needs (not the memory tools A7.4), so the framework is buildable at P0. |
| A8.1 | Monitor | A8.0, A6.2, A6.1, A6.3 | §19.1 | `detect_anomaly` over canonical series. `[P0]` |
| A8.2 | Decompose ★ | A8.0, A6.2, A6.1, A6.3 | §19.1 | `decompose_change` mix/rate/interaction. `[P1]` |
| A8.3 | Diagnose ★ | A8.0, A6.2, A6.1, A6.3 | §19.4 | Hypothesis-tree RCA, SQL-verified. `[P1]` |
| A8.4 | Critic ★ | A8.0, A6.1–A6.3, A7.4 | §19.3 | Adversarial refutation; PASS/DOWNGRADE/DROP. Uses `recall_prior` → depends on A7.4 (which transitively pulls report-mcp + memory). `[P1]` |
| A8.5 | Prescribe | A8.0, A6.4 | §19.1 | Powered experiment backlog. `[P1]` |
| A8.6 | Narrator | A8.0, A6.5 | §19.1 | Renders brief via `render_brief` (A6.5) for the minimal loop; full loop also calls `save_diagnosis` → adds A7.4. `[P0 minimal]` |
| A8.7 | Orchestrator | A8.1–A8.6, A7.4 | §19.3, §19.6 | Plans run, drives FSM, budget, routes to Critic. Calls `recall_prior` → depends on A7.4 (not raw memory). |

### T9 — Orchestration runtime `[P1/P2]` (depends: T8)
| ID | Artifact | Depends on | Bible | Notes |
|----|----------|-----------|-------|-------|
| A9.1 | Pipeline runner (PLAN→MONITOR→…→END FSM) ★ | A8.7 | §19.3 | Executes a full run; consumed by eval runner. |
| A9.2 | Scheduler entrypoint (Cloud Scheduler/cron) | A9.1 | §19.6, §23.3 | Autonomy. `[P2]` |
| A9.3 | run_state/audit wiring | A9.1, A7.1 | §22.5 | Budget enforcement + reconstructability. |

### T10 — Evaluation harness `[P1]` — THE TRUST PROOF (depends: T4.7, T9, T6, T5)
| ID | Artifact | Depends on | Bible | Notes |
|----|----------|-----------|-------|-------|
| A10.1 | `helios_eval.fct_daily_funnel_base` (frozen extract) | A4.7, A6.1 | §20.2 | Baseline copy extracted from `fct_daily_funnel` via `warehouse-mcp.run_query`; never mutate the public source. (`_perturbed` + `labels` are produced by the injector A10.2, not here.) |
| A10.2 | `eval/injector.py` ★ | A10.1, A6.1 | §20.2 | Seeded rate/volume perturbation + ground-truth labels. |
| A10.3 | `eval/scenarios/*.yaml` (50) ★ | A10.2 | §20.3 | Coverage buckets incl. seasonality decoys + controls. |
| A10.4 | `eval/runner.py` | A9.1, A10.2 | §20.6 | Points pipeline at perturbed copy; runs all 7 agents. |
| A10.5 | `eval/scorers/{rootcause,decomposition,detection,dollars,hallucination,faithfulness}.py` ★ | A10.4 | §20.4, §20.6 | Deterministic Python scoring. |
| A10.6 | `eval/report.py` (+ `eval/history/`) | A10.5 | §20.9 | Results table → PR comment. |
| A10.7 | `eval/gates.yaml` + `eval/baselines/main.json` ★ | A10.5 | §20.8 | Regression gates; hard-zero hallucination. |

### T11 — CI/CD `[P1]` (depends: dbt project + eval harness)
| ID | Artifact | Depends on | Bible | Notes |
|----|----------|-----------|-------|-------|
| A11.1 | `.github/workflows/ci.yml` ★ | A4.12, A5.2, A10.* | §15, §20.8 | dbt build+test + eval (smoke on push, full 50 on PR to main). Continuity guard. |

### T12 — Product surface `[P0→P2]` (depends: T6.5 + T8)
| ID | Artifact | Depends on | Bible | Notes |
|----|----------|-----------|-------|-------|
| A12.1 | Decision Brief template/renderer (`render_brief`) | A6.5, A8.6 | §4.7, §18.8 | The primary product surface. |
| A12.2 | `export` (pdf/slack) | A12.1 | §18.8 | Distribution. |
| A12.3 | Drill-down conversational interface (secondary) | A8.*, A6.2 | §4.4 | Late; explicitly secondary. `[P2]` |

### T13 — Docs & continuity `[parallel throughout]`
| ID | Artifact | Depends on | Bible | Notes |
|----|----------|-----------|-------|-------|
| A13.1 | README, runbook, ADRs (architecture decision records) | ongoing | §12 | Keep in lockstep with code. |
| A13.2 | This `DEPENDENCY_MAP.md` + the Bible | — | — | The two continuity anchors. |
| A13.3 | `analyses/adhoc_mix_shift_explore.sql` ∥ | A4.6 | §16.1 | Non-materialized exploratory analysis; not on the run path. |

---

## 2. Dependency DAG (high-level)

```text
[T0 repo / GCP+IAM / dbt cfg / CLAUDE.md]
   |
   +─► [T1 macros (get_event_param, sessionize, channel_group★) + src_ga4 + seed]
   |        |
   |        ▼
   |   [T2 staging: stg_ga4__events, stg_ga4__event_params]
   |        |
   |        ▼
   |   [T3 int_ga4__sessionized ★] ──► [T3 int_ga4__funnel_steps ★]      ◄── DATA KEYSTONE
   |        |                                   |
   |        ▼                                   ▼
   |   [T4 dims: date∥, channels, users, items∥]   [T4 fct_funnel ★] ──► [fct_daily_funnel ★]
   |        |        \                               |          \              |
   |        |         ▼                              ▼           ▼             |
   |        |   [fct_orders∥]►[fct_order_items∥] [fct_funnel_by_dim] [fct_cohorts]
   |        |________________________________________|____________________|
   |                                                  ▼
   |                              [T5 semantic_layer.yaml registry ★★]     ◄── GOVERNANCE KEYSTONE
   |                                                  |
   |                      ┌───────────────────────────┴───────────────┐
   |                      ▼                                            ▼
   |               [T6 semantic-mcp ★] ──governed SQL──► [T6 warehouse-mcp ★] (needs T0 IAM)
   |
   │  ── data-independent parallel track (start at T0) ──
   +─► [T6 stats-mcp ★ : decompose_change*]            ◄── THESIS CENTERPIECE
   +─► [T6 experiment-mcp]
   +─► [T6 report-mcp core: render_brief / export]   (no memory dependency)
   +─► [T7 memory DDL ★ + seeds∥] ──► [T7 report-mcp memory tools (A7.4): save_diagnosis / recall_prior]

[ all T6 MCP servers ] + [ T7 memory ]
                      ▼
        [T8 agent framework ★] ─► Monitor ─► Decompose★ ─► Diagnose★ ─► Critic★
                      │                 └─► Prescribe   └─► Narrator        │
                      ▼                                                     │
              [T8 Orchestrator] ◄───────────────────────────────────────────┘
                      ▼
        [T9 pipeline runner ★ + scheduler + audit]
                      ▼
        [T10 eval: injector★ ─► scenarios★ ─► runner ─► scorers★ ─► report ─► gates★/baseline]  ◄── TRUST PROOF
                      ▼
        [T11 CI gating ★]   +   [T12 Decision Brief / export]   +   [T13 docs]
```

No edge points upward → the graph is acyclic; any topological sort is a valid build order.

---

## 3. Recommended generation order (phased, topologically safe)

Build in **milestones**; never start a milestone until the prior one is green (`dbt build` + tests, and from M7 onward the eval harness). Mapped to Bible §23 phases.

| # | Milestone | Artifacts | Gate to advance |
|---|-----------|-----------|-----------------|
| **M0** | Foundation `[P0]` | A0.1–A0.5 (repo, GCP/IAM, dbt cfg, CLAUDE.md, mcp stub) | `dbt debug` connects; ADC authenticates. |
| **M1** | dbt sources & macros `[P0]` | A1.1–A1.6 | macros compile; seed loads. |
| **M2** | Staging `[P0]` | A2.1–A2.3 | staging tests pass; row counts sane. |
| **M3** | **Sessionization & funnel flags `[P0]`** ★ | A3.1, A3.2, A3.3 | funnel monotonicity test passes; session_key unique. |
| **M4** | Core + finance marts `[P0]` | A4.1–A4.9, A4.12 | `revenue_reconciles` to the cent (§23.1 exit); channel `accepted_values` passes. |
| **M5** | **Semantic registry `[P0]`** ★★ | A5.1, A5.2 | registry compiles; 0 dangling references. |
| **M6** | Grounding MCP pair `[P0]` | A6.0, A6.2 (semantic), A6.1 (warehouse) | `build_query→dry_run→run_query` round-trips; budget gate fires; reconcile matches. |
| **M6b** | Stats/experiment/report MCP ∥ `[P0/P1]` | A6.3 (stats★), A6.4, A6.5 (report-mcp core) | `decompose_change` unit tests vs hand-worked mix/rate/interaction examples pass; `render_brief` emits a brief. |
| **M7** | Minimal loop `[P0]` (L1 exit) | A8.0 (framework, scoped to A6.0–A6.3/A6.5), A8.1 (Monitor), A8.6 (minimal Narrator via `render_brief`), A12.1 (basic brief) | one anomaly → brief in <5 min; 0 hallucinated columns. **L1 DONE.** (All deps — incl. report-mcp core A6.5 — exist from M6/M6b.) |
| **M8** | Memory + report-mcp memory tools `[P1]` | A7.1–A7.3, A7.4 | save/recall round-trips; seeds loaded; vector ANN recall works. |
| **M9** | Full agent loop `[P1]` | A8.2 Decompose, A8.3 Diagnose, A8.4 Critic, A8.5 Prescribe, A8.7 Orchestrator, A9.1 runner, A9.3 audit, A4.13 exposures (finalize) | a real run produces PASS findings with significance + $ + action. |
| **M10** | **Eval harness + CI `[P1]`** ★ (L2 exit) | A10.1–A10.7, A11.1 | ≥85% top-1 vs ≤45% baseline; hallucination 0%; cost under budget. **L2 DONE.** |
| **M11** | Autonomy & depth `[P2]` (L3 exit) | A9.2 scheduler, A4.11 cohorts, `forecast`/`cohort_retention`/`rfm_segment` usage, full Critic battery, A12.2/A12.3 | <5 min/run on schedule; accuracy holds across all dims. **L3 DONE.** |
| **M12+** | Productionization / frontier `[P3/P4]` | per §23.4–23.5 | warehouse-agnostic adapters; causal inference; auto-executed experiments. |

---

## 4. Critical path (the spine)

The longest must-be-sequential chain — and therefore the schedule-determining path — to the **L2 trust milestone (the 85%-vs-45% claim)**:

```text
T0 foundation → A1.* macros → A2.1 staging → A3.1 sessionized → A3.2 funnel_steps
   → A4.6 fct_funnel → A4.7 fct_daily_funnel → A5.1 semantic registry
   → A6.2 semantic-mcp (+ A6.1 warehouse-mcp) → A6.3 stats-mcp/decompose_change
   → A8.0 agent framework → A8.1→A8.2→A8.3→A8.4 (Monitor→Decompose→Diagnose→Critic) → A8.7 Orchestrator
   → A9.1 pipeline runner → A10.2 injector → A10.3 scenarios → A10.4 runner → A10.5 scorers → A10.7 gates → A11.1 CI
```

**Co-critical branch (must converge before A10.4).** Because the eval runner executes *all seven* agents, the Critic's `recall_prior` (A8.4) and the Narrator's `save_diagnosis` (A8.6) require the memory branch:

```text
A7.1 memory DDL → A7.2 vector store + A7.3 seeds → A7.4 report-mcp memory tools
   → consumed by A8.4 Critic (recall_prior) and A8.6 Narrator (save_diagnosis) → A10.4 full-pipeline run
```

This branch runs in parallel with the spine but is *co-critical from A8.4 onward* — the full 7-agent eval cannot run without it.

Anything **not** on the spine *or* the co-critical branch (finance facts, cohorts, experiment-mcp, the scheduler, drill-down UI, docs) can be built in parallel or deferred without delaying the headline claim.

---

## 5. Most important artifacts (ranked, with why)

1. **A5.1 `semantic_layer.yaml` registry ★★** — the governance keystone. Every governed query, every metric, `semantic-mcp`, and the hallucination-rate guarantee derive from it. For continuity, this YAML + the Bible is enough to regenerate all SQL. **Highest leverage.**
2. **A3.1/A3.2 sessionization + `reached_*` flags ★** — the data keystone. If sessionization or the monotonic funnel flags are wrong, *every* downstream number is silently wrong. Maximum test coverage here.
3. **A6.3 `stats-mcp` / `decompose_change` ★** — the thesis centerpiece (mix vs rate vs interaction, Simpson's-paradox defense). Data-independent, so build and unit-test it early against hand-worked examples; it is also the single most interview-defensible component.
4. **A10.* eval harness + scenarios + gates ★** — the trust proof and the *continuity* guard: the CI gate is what lets a future engineer refactor without silently regressing the 85% claim. This is what separates Helios from a demo.
5. **A6.1/A6.2 `warehouse-mcp` + `semantic-mcp` ★** — the grounding boundary made physically enforceable (only path to SQL; mandatory dry-run/byte budget).
6. **A0.2 CLAUDE.md + A13.2 this map + the Bible** — the human/AI continuity anchors. Without them the graph must be rediscovered.
7. **A8.0 agent framework + A8.4 Critic ★** — the control plane and the adversarial verifier; the Critic is why findings are trustworthy enough to ship autonomously.

---

## 6. What to generate FIRST (the immediate next 6 steps)

These unblock the widest fan-out with the least prerequisite. Do them in this order:

1. **A0.1–A0.4** — repo scaffold, GCP/IAM/ADC, `dbt_project.yml`/`profiles.yml`/`packages.yml`, and **CLAUDE.md** (so all subsequent AI-assisted work is grounded).
2. **A1.1–A1.6** — the four macros (esp. `channel_group_case` ★), source declaration, and seed.
3. **A2.1–A2.3** — staging models + tests.
4. **A3.1 → A3.2** — sessionization, then `reached_*` funnel flags. *(Spend disproportionate care + tests here.)*
5. **A5.1** — the semantic registry, immediately after the funnel facts (A4.6/A4.7) exist. *(This is the governance keystone — front-load it.)*
6. **A6.3 `stats-mcp` in parallel** from day one (data-independent): implement `decompose_change` with unit tests before any agent needs it.

> **Continuity rule of thumb:** front-load the two keystones (A3.* sessionization, A5.1 registry) and the data-independent thesis core (A6.3), because they have the largest downstream blast radius and are the artifacts most expensive to get wrong late.

---

## 7. Parallelizable tracks (independent subgraphs)

To compress wall-clock without violating the DAG, three tracks can run concurrently after T0:

- **Track A — Data spine (critical path):** T1 → T2 → T3 → T4(core) → T5 → T6(semantic+warehouse).
- **Track B — Math & experiment (data-independent):** A6.3 `stats-mcp` (incl. `decompose_change`, `forecast`, `cohort_retention`, `rfm_segment`) + A6.4 `experiment-mcp`, each with their own unit tests. Joins Track A at T8.
- **Track C — Memory & finance (independent):** A7.1–A7.3 memory DDL/seeds + A4.8/A4.9 finance facts + A4.1 `dim_date`/A4.4 `dim_items`. Track C gates `report-mcp` (A6.5) and cohorts (A4.11).

All three converge at **T8 (agents)**, which is the first artifact requiring the full stack.

---

## 8. Continuity guardrails (do not skip)

- **Never let the registry (A5.1) drift from the marts (T4).** A column rename in a fact must update exactly one YAML; CI referential-integrity (A5.2) enforces it.
- **The CI eval gate (A11.1) is the regression firewall.** Once M10 is green, no change merges that drops top-1 accuracy >2pts or introduces any hallucination. This is the single most important continuity mechanism.
- **Keep CLAUDE.md and this map updated as artifacts land** — they are the resume points for any future build session.
- **Seed memory (A7.3) before relying on the Critic's seasonality refutations** — an unseeded `seasonality_calendar` makes the Critic blind to known confounds (e.g., the Black Friday 2020 / January-trough swings in this dataset window).
- **Honor the keystones' test budgets:** sessionization, funnel monotonicity, revenue reconciliation, and `decompose_change` algebra each need golden-value tests, because they fail *silently* (wrong numbers, not errors).
- **Keep the registry filename canonical.** The semantic registry is `models/semantic/semantic_layer.yaml` (the v2 registry; the retired v1 `semantic_models.yml` is archived in `docs/archive/superseded/`); `semantic-mcp` in `mcp_servers.yaml` must point its `registry:` at that exact path. A5.1 and A6.2 share one physical file — a divergence here silently desyncs the governed-SQL guarantee.
- **Pin the `fct_daily_funnel` source.** It aggregates `fct_funnel` (A4.6) — the source carrying `session_revenue` — not `int_ga4__funnel_steps`; the §16.10 sample is an abbreviated counts-only illustration. Getting this wrong drops `revenue` from the daily grain and breaks the eval injector's dollar-at-risk labels.
