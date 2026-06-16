# CLAUDE.md — Helios

> Operating manual for Claude Code (and any AI agent) working in this repo. Read this first, every session. It is the **continuity anchor**: canonical vocabulary, the non-negotiable rules, conventions, and where to find depth. Keep it updated as artifacts land.

---

## 1. What Helios is

**Helios is the Autonomous Growth Diagnosis Engine** — an always-on "AI Growth Analyst" that diagnoses *why* an e-commerce funnel moved, distinguishes **mix-shift from rate-change**, prices the movement in **dollars of revenue-at-risk**, prescribes a **prioritized, statistically-defensible experiment backlog**, and ships an executive **Decision Brief** — all grounded in **governed SQL it never authors by hand** and graded by an **offline eval benchmark**.

It runs on the public GA4 dataset `bigquery-public-data.ga4_obfuscated_sample_ecommerce` (Google Merchandise Store, ~2020-11-01 → 2021-01-31).

**Anti-product stance (do not drift into these):** Helios is **not** a BI dashboard, **not** an ad-hoc SQL chatbot, **not** a generic "ask-your-data" tool. Conversation is a *secondary* drill-down surface. The product's heartbeat is the **autonomous scheduled run**.

---

## 2. Source of truth & precedence

| Doc | Role |
|-----|------|
| `docs/architecture/HELIOS_PROJECT_BIBLE.md` | The full 25-section spec (what every artifact is). Rebuild-from-scratch reference. |
| `docs/planning/DEPENDENCY_MAP.md` | Build order, dependencies, keystones, what-to-build-next (T0–T13, milestones M0–M12). |
| **This file** | Day-to-day operating rules + canonical vocabulary. |

**Precedence:** the Bible's **Canonical Reference Card** wins over any prose anywhere. This file mirrors it; if they ever disagree, the Reference Card is correct and both should be fixed.

---

## 3. The five non-negotiable principles

1. **Grounding over generation.** The LLM **never authors raw SQL** and **never computes a statistic** in prose. It composes governed metrics via `semantic-mcp` and calls deterministic tools via `stats-mcp`.
2. **Verify-then-trust.** Every query is `dry_run`-cost-checked + schema-validated; every result is `reconcile`-checked against canonical totals; every finding is attacked by the **Critic** before it ships.
3. **Determinism where it matters.** All math (decomposition, significance, power, forecasting) runs in real Python (scipy/statsmodels/prophet), seeded — never in token-space.
4. **Every finding is actionable.** A finding without a significance test, a dollar impact, and a recommended action is not a finding.
5. **Proactive, not reactive.** Build for the scheduled autonomous run first; conversation is secondary.

### Grounding rules G1–G5 (enforced structurally + behaviorally)
- **G1** — Never emit raw SQL. To get data, call `semantic-mcp.build_query(metric, dims, filters, window)` or `get_metric(name)`.
- **G2** — Never compute a statistic in prose. Anomaly scores, decompositions, significance, forecasts, power → `stats-mcp` / `experiment-mcp` only. Numbers in the brief are tool outputs verbatim.
- **G3** — `warehouse-mcp.dry_run` **before** every `run_query`. Over-budget ⇒ narrow window/dims, do not retry blindly.
- **G4** — Reconcile aggregates against `warehouse-mcp.reconcile`; >0.5% drift fails the finding.
- **G5** — Use **only** canonical metric/dimension names. An unknown name is a hard error, not a fallback to free SQL.

---

## 4. Canonical vocabulary (NEVER paraphrase — these are physical names)

### Macro funnel (session-scoped; session key = `(user_pseudo_id, ga_session_id)`)
```
session_start → view_item → add_to_cart → begin_checkout → add_shipping_info → add_payment_info → purchase
```
Report step-to-step rates **and** overall `session_conversion_rate = purchasing_sessions / sessions`.

### Metrics (snake_case)
`sessions`, `users`, `new_users`, `returning_users`, `engaged_sessions`, `engagement_rate`, `view_item_sessions`, `add_to_cart_sessions`, `begin_checkout_sessions`, `purchasing_sessions`, `session_conversion_rate`, `view_to_cart_rate`, `cart_to_checkout_rate`, `checkout_to_purchase_rate`, `cart_abandonment_rate`, `checkout_abandonment_rate`, `transactions`, `revenue`, `gross_revenue`, `net_revenue`, `aov`, `items_per_transaction`, `revenue_per_session` (RPS), `revenue_per_user` (ARPU).

### Dimensions
`device_category`, `operating_system`, `browser`, `country`, `region`, `channel_group`, `source`, `medium`, `campaign`, `landing_page`, `item_category`, `item_name`, `is_new_user`, `day`, `week`, `session_number_bucket`.

### Channel groups — exactly 10 (no "Paid Other")
`Direct`, `Organic Search`, `Paid Search`, `Display`, `Paid Social`, `Organic Social`, `Email`, `Affiliates`, `Referral`, `Other`.

### MCP servers & tools
| Server | Role | Tools |
|--------|------|-------|
| `warehouse-mcp` | Sole BigQuery client (HTTP) | `list_tables`, `describe_table`, `dry_run`, `run_query`, `reconcile` |
| `semantic-mcp` | **Only path to SQL** (stdio) | `get_metric`, `list_dimensions`, `build_query` |
| `stats-mcp` | **Only path to math** (stdio) | `detect_anomaly`, `decompose_change`, `significance_test`, `forecast`, `cohort_retention`, `rfm_segment` |
| `experiment-mcp` | Powered backlog (stdio) | `power_analysis`, `runtime_estimate`, `design_experiment` |
| `report-mcp` | Brief + memory (stdio) | `render_brief`, `export`, `save_diagnosis`, `recall_prior` |

### Agents (7) — Claude Agent SDK, plan-execute-critique
`Orchestrator` (Opus), `Monitor` (Sonnet), `Decompose` (Sonnet), `Diagnose` (Opus), `Prescribe` (Sonnet), `Narrator` (Sonnet), `Critic` (Opus). Per-agent MCP tool allow-lists are enforced (Bible §18.9) — e.g. the Narrator cannot call `run_query`.

### Core decomposition identity (the technical centerpiece — `stats-mcp.decompose_change`)
For aggregate rate `R = Σ_i (w_i · r_i)` (segment weight × segment rate), `ΔR` from `t0→t1` splits as:
```
mix_effect   = Σ Δw_i · r_i(t0)     # traffic composition changed
rate_effect  = Σ w_i(t0) · Δr_i     # in-segment behavior changed
interaction  = Σ Δw_i · Δr_i        # both moved together
ΔR = mix_effect + rate_effect + interaction
```
This is how Simpson's paradox is dissolved. Drill into **rate** effects (real behavior change), not **mix** effects (composition artifacts).

### Success-metric targets
Root-cause accuracy **≥85%** (vs **≤45%** naive baseline); time-to-diagnosis **<5 min/run**; **0** hallucinated columns/metrics (100% governed SQL); **100%** of findings carry significance + dollar impact; query cost per run **≤ 5 GiB** (the fixed byte budget).

---

## 5. dbt & data conventions

- **Layers / prefixes:** `stg_<source>__<entity>` (staging) → `int_<source>__<entity>` (intermediate) → `fct_*` / `dim_*` (marts) → `models/semantic`. Source group: `src_ga4`. snake_case everywhere.
- **Materializations:** staging = `view`; intermediate = `ephemeral`; marts/core = `incremental` (`insert_overwrite`, partition by `event_date`, cluster by `device_category, channel_group`); finance/growth = `table`; semantic = `view`.
- **Funnel flags are `reached_*`, max-downstream (monotonic).** `reached_add_to_cart` = the session reached add_to_cart **or any later stage**. This guarantees `sessions ≥ reached_view_item ≥ … ≥ reached_purchase`, so step rates are always ≤ 1. The names `did_*` are **retired**.
- **Session key (one canonical expression):** `session_key = TO_HEX(MD5(CONCAT(user_pseudo_id, '-', CAST(ga_session_id AS STRING))))`; `sessions = COUNT(DISTINCT session_key)`. Never `FARM_FINGERPRINT`, never `COUNT(*)`.
- **Engaged session:** `session_engaged = '1' OR engagement_time_msec >= 10000` (use `>=`, no extra clauses).
- **`traffic_source` gotcha:** event-level `traffic_source.*` is **user first-touch**, not session source. Prefer session-scoped `event_params.source/medium`; fall back to `traffic_source` only when null.
- **Money & rates:** use only GA4 `_in_usd` columns; never aggregate non-USD twins. Compute rates as `SUM(numerator)/SUM(denominator)` after grouping — **never** an average of per-segment ratios (this is the Simpson's-paradox defense).
- **Single sources of truth:** channel grouping lives **only** in the `channel_group_case()` macro (`macros/channel_group.sql`); metric/dimension definitions live **only** in `semantic/semantic_layer.yaml` (the v2 registry, **at the repo root — deliberately OUTSIDE `models/`** so dbt doesn't parse it as a schema file; the retired v1 `semantic_models.yml` is archived in `docs/archive/superseded/`). `semantic-mcp`'s `registry:` in `mcp_servers.yaml` and `SemanticLayer.DEFAULT_REGISTRY` must point at that exact path.

---

## 6. Repository layout

```
helios/
├─ README.md · CLAUDE.md (this file) · .gitignore · MIGRATION_REPORT.md
├─ docs/
│  ├─ architecture/  HELIOS_PROJECT_BIBLE · DATA_MODEL · DBT_GUIDE · MCP_ARCHITECTURE · AGENT_ARCHITECTURE · METRIC_DEPENDENCY_GRAPH · METRIC_GOVERNANCE_GUIDE
│  ├─ planning/      DEPENDENCY_MAP · DEVELOPMENT_PLAN · IMPLEMENTATION_PLAYBOOK · LEAN_SCOPE
│  ├─ strategy/      CLAUDE_CODE_WORKFLOW · INTERVIEW_GUIDE · RED_TEAM_REVIEW
│  └─ archive/       (frozen intermediate fragments + superseded/semantic_models.yml)
├─ semantic/ semantic_layer.yaml               # the governed registry (v2, 49 metrics) — OUTSIDE models/ so dbt won't parse it
├─ eval/
│  ├─ scenarios/     scenarios.yaml + 01–07_*.yaml + _VALIDATION.md   (50-scenario benchmark)
│  └─ benchmark_results/
└─ dbt/ · mcp/ · agents/ · backend/ · frontend/ · tests/ · scripts/ · notebooks/   # implementation code — empty until M0+ (each has a placeholder README)
```

### BigQuery datasets
`bigquery-public-data.ga4_obfuscated_sample_ecommerce` (read-only source) · `helios` marts (`helios.marts.*`) · `helios_memory` · `helios_eval` · dbt targets `helios_dev` / `helios_prod`.

---

## 7. Commands

> Platform is **Windows / PowerShell**. The repo is currently **documentation + assets only** (no implementation code yet). The commands below are the *canonical interface* — wire them up as each milestone lands (see `docs/planning/DEPENDENCY_MAP.md` §3). Mark a command "live" in this file once it actually works.

```powershell
# dbt (once M0–M5 exist)
dbt deps
dbt build                      # full DAG + tests
dbt build --select staging     # one layer
dbt test --select fct_funnel    # one model's tests
dbt build --select +fct_daily_funnel   # model + upstream

# MCP servers — stdio servers
python -m helios.mcp.stats       # LIVE — decompose_change / significance_test / critique_decomposition
python -m helios.mcp.semantic    # LIVE — build_query / get_metric / list_metrics / list_dimensions (governed SQL)
python -m helios.mcp.warehouse   # LIVE — dry_run / run_query / reconcile (sole BigQuery client; needs ADC)
python -m helios.mcp.report      # LIVE — save_diagnosis / recall_prior / check_suppression (memory)
python -m helios.mcp.experiment  # LIVE — power_analysis / runtime_estimate / design_experiment

# Eval harness (once M10 exists)
python -m helios.eval.runner --smoke    # 12-scenario subset (every push)
python -m helios.eval.runner --full     # all 50 scenarios (PR to main)
```

### Required environment variables
`GOOGLE_APPLICATION_CREDENTIALS` (BigQuery SA, read-only) · `HELIOS_WH_TOKEN` (warehouse-mcp bearer) · `ANTHROPIC_API_KEY` (agents).

---

## 8. Keystones — get these right, test them hard (they fail SILENTLY)

1. **`int_ga4__sessionized` + `int_ga4__funnel_steps`** — if sessionization or the `reached_*` flags are wrong, every downstream number is silently wrong.
2. **`semantic/semantic_layer.yaml`** — the governance keystone; all governed SQL derives from it.
3. **`stats-mcp.decompose_change`** — unit-test against hand-worked mix/rate/interaction examples (golden values).
4. **Revenue reconciliation** — `fct_orders` revenue must match the source to the cent (`revenue_reconciles` test).
5. **`fct_daily_funnel`** aggregates `fct_funnel` (which carries `session_revenue`) — not `int_ga4__funnel_steps`. Dropping revenue here breaks the eval's dollar-at-risk labels.

The **CI eval gate** (`.github/workflows/ci.yml` + `eval/gates.yaml`) is the regression firewall: once green, no change may drop top-1 accuracy >2pts or introduce any hallucination.

---

## 9. How to use Claude Code on this repo

- **Plan first.** For any multi-file change, use plan mode and check it against `DEPENDENCY_MAP.md` build order before editing. Never build an artifact before its dependencies (the map is a valid topological sort).
- **TDD on SQL.** Write the dbt test / golden-value test *first*, then make it pass. Keystone transforms get golden tests because they fail silently.
- **Eval-driven dev for agents.** Changes to `models/`, `semantic/`, `agents/`, or `eval/` must keep the benchmark ≥85% top-1 and hallucination = 0. Run the smoke subset locally before pushing.
- **Parallelize independent tracks** (subagents): the data spine, the data-independent math (`stats-mcp`/`experiment-mcp`), and memory/finance can progress concurrently (DEPENDENCY_MAP §7).
- **Keep docs in lockstep.** When you add/rename an artifact, update `DEPENDENCY_MAP.md` and, if a canonical name changes, the Bible's Reference Card and this file. These three are the resume points for the next session.

### Do / Don't
- ✅ Compose metrics via `semantic-mcp`; route all math through `stats-mcp`; `dry_run` before `run_query`.
- ✅ Use exact canonical names; add new metrics by editing the registry YAML, not by hand-writing SQL.
- ✅ Make every finding carry significance + dollar impact + an action.
- ❌ Don't hand-author SQL in agent prompts or Python, invent metric synonyms, compute stats in prose, or skip the Critic.
- ❌ Don't add an 11th channel group, reintroduce `did_*` flags, or use a non-canonical session-key expression.
- ❌ Don't widen scope into a dashboard/chatbot — that's the anti-product.

---

## 10. Current status & next step

> Last refreshed 2026-06-16. A working **MVP is built and deployed** — the docs suite is no longer the only artifact.

### Verified end-to-end on REAL GA4 (2026-06-16)
Run against `bigquery-public-data.ga4_obfuscated_sample_ecommerce` in project `helios-mvp`:
- **`dbt build` → PASS=62 WARN=1 ERROR=0.** 4.3M events → 360k sessions → `fct_funnel` → 64k `fct_daily_funnel`. Keystones green: `assert_funnel_monotonicity`, `assert_session_conversion_rate_bounds`, both unit tests. (The 1 WARN = `test_revenue_reconciles_fct_funnel_session_revenue`, 1 row — `severity: warn`; investigate later.)
- **Governed heartbeat on the real marts** (`python -m helios.run --source bigquery`): produced a real brief — session conversion 1.64%→1.06% (−0.59pt, p≈9e-9), dominant=rate, drivers Referral/desktop+mobile, −$7,538. Whole governed path exercised (build_query → dry_run → run_query → decompose → critic).
- **Grounded LLM brief** (`brief.py`, real Gemini key): every number in the narrative traced to the two tool calls and matched the deterministic run exactly — G1/G2 proven on real data.
- **Datasets:** after the `dbt_project.yml` fix, marts land in **`helios_dev_marts`** (target `helios_dev` + `+schema: marts`), staging in `helios_dev_staging`. App/CLI defaults updated to `helios_dev_marts`.

**Known issues / honest caveats:** the labeled eval's 100% is *controlled-attribution* accuracy on synthesized data (not real-world accuracy — frame precisely); the dashboard demo runs on *synthetic* data; dbt group/access governance is deferred; mart partitioning/clustering is deferred (models pin `materialized='table'` in-file); 1-row revenue-reconcile WARN.

### Architecture note — the MVP is *flattened*, not the full agent/MCP mesh (yet)
The Bible specifies 5 MCP servers + 7 SDK agents. The shipped MVP collapses that into a single in-process Python package + a Streamlit app, holding the **five non-negotiable principles** (§3) by structure rather than by separate servers: governed marts (no hand SQL in the diagnosis path), deterministic math in real Python, every finding carrying significance + dollars + an action. **The top-level `mcp/`, `agents/`, `backend/`, `frontend/` dirs are still empty placeholders** — working code lives in `helios/` + root scripts + `app.py`.

### Built & working (live)
- **Data spine (dbt):** `models/staging → intermediate → marts` (`stg_ga4__events`/`event_params`, `int_ga4__sessionized`, `int_ga4__funnel_steps`, `fct_funnel`, `fct_daily_funnel`, `fct_orders`, `dim_channels`, `dim_date`) + the four macros (`channel_group`, `sessionize`, `get_event_param`) + seed. `dbt_project.yml`/`profiles.yml`/`packages.yml` present.
- **Semantic registry:** `semantic/semantic_layer.yaml` (governance keystone; at repo root, outside `models/`).
- **Math engine:** `helios/stats/decompose.py` (mix/rate/interaction — the centerpiece) + `significance.py` (two-proportion z-test). Golden-tested in `tests/test_decompose.py`.
- **Diagnosis:** `helios/diagnosis.py` (shared by CLI + dashboard) → `diagnose.py` (templated Decision Brief, no LLM).
- **Grounded LLM brief:** `helios/llm/tools.py` (`GovernedTools` — the LLM's only data path; logs every call) + `brief.py` (Gemini, provider-swappable) → `brief.py` CLI.
- **Critic (verify-then-trust):** `helios/critic.py` — adversarial checks (additivity/reconcile, significance, mix-vs-rate framing, dollar sanity, data-quality) run on every `Diagnosis` before it ships; exposed to the LLM as a governed tool.
- **Eval benchmark:** two harnesses. `helios/eval/` (injector + baseline) is the original 8-scenario BigQuery-backed runner (`eval_run.py`). `helios/eval/labeled.py` is the **offline 50-scenario firewall** over `eval/scenarios/scenarios.yaml` (all 7 buckets: rate/mix/multi/seasonality/control/data-quality) — no BigQuery, run via `eval_labeled.py`. Both pure-Python tested in `tests/`.
- **Synthetic "live" data:** `helios/synth/generator.py` + `synth_run.py` load a rolling 90-day `fct_daily_funnel` into `helios_live` so the demo shows current weeks.
- **Dashboard:** `app.py` (Streamlit, dark theme, week selector, "Generate AI Brief") — **live on Streamlit Cloud** (link in README).
- **CI gate:** `.github/workflows/ci.yml` + `eval/gates.yaml` run pytest + the labeled eval and fail on accuracy regression or any hallucinated segment. `main` is branch-protected on the `test-and-eval-gate` check.
- **stats-mcp (the first real MCP server):** `helios/mcp/stats.py` — a stdio FastMCP wrapper exposing `decompose_change`, `significance_test`, `critique_decomposition` over MCP (`python -m helios.mcp.stats`). Declared in `mcp_servers.yaml`; Claude Code launches it via `.mcp.json`. This closes the one technical artifact LEAN_SCOPE requires for **v1** (one governed MCP server + MCP client). Tested in `tests/test_mcp_stats.py`.
- **Autonomous run (the heartbeat — v2 P0):** `helios/run.py` (`python -m helios.run`) does headless load → diagnose → critic → dated Markdown brief (`helios/report/brief_md.py`), with a `synthetic`|`bigquery` source switch. Scheduled daily by `.github/workflows/daily-brief.yml` (synthetic source, uploads the brief as an artifact; optional Slack via `HELIOS_SLACK_WEBHOOK`). This is the first step turning Helios from reactive (dashboard) to **proactive** (principle #5). Tested in `tests/test_run.py`.
- **experiment-mcp + powered experiments (v2 P3, complete):** `helios/experiment/` sizes a defensible A/B test for a finding — `power.py` (two-proportion sample size + runtime, scipy) and `design.py` (`design_experiment` → hypothesis, primary metric, guardrails, sample size, runtime, feasibility). Exposed at `helios/mcp/experiment.py` (`python -m helios.mcp.experiment`: `power_analysis`/`runtime_estimate`/`design_experiment`). The Decision Brief now carries a **Recommended experiment (powered)** section for rate-dominant SHIP findings, sized on the pooled regressed population (principle #4 fully met). Tested in `tests/test_experiment.py` + `tests/test_mcp_experiment.py`. **Five live MCP servers now** (stats, semantic, warehouse, report, experiment).
- **report-mcp + memory (the run gets smart — v2 P2, complete):** `helios/memory/` adds the state that stops the heartbeat re-paging the team. `store.py` (`MemoryStore`, JSONL) persists findings keyed by a fingerprint (dominant effect + top segment + direction); `seasonality.py` is a calendar of known events (Black Friday, Cyber Monday, Christmas peak, New Year, post-holiday January trough — the same events behind the eval's `seasonality_decoy` bucket); `suppression.py` `decide()` returns **NEW** (alert + remember) or suppresses **SEASONAL / REFUTED / IMMATERIAL / REPEAT**. `helios/run.py` consults it: only a NEW finding is saved and pages Slack; the brief carries a status banner. Exposed at `helios/mcp/report.py` (`python -m helios.mcp.report`: `save_diagnosis`/`recall_prior`/`check_suppression`). Tested in `tests/test_memory.py` + `tests/test_mcp_report.py`.
- **semantic-mcp + warehouse-mcp (governed data path — v2 P1, complete):** `helios/semantic/layer.py` (`SemanticLayer.build_query`) composes governed SQL purely from the registry's `sql_definition`s; unknown/unsupported names and mixed grains are hard errors (G1/G5). `helios/warehouse/client.py` (`Warehouse`) is the sole BigQuery client: `run_query` dry-run cost-checks against a 5 GiB budget before executing (G3), and `reconcile` checks aggregates within 0.5% (G4). **`helios/diagnosis.load_weekly` now composes via `build_query` and executes via `Warehouse` — `WEEKLY_SQL` is deleted**, so the diagnosis path no longer hand-authors SQL and reads `fct_funnel` (session grain) through the registry. Both exposed over MCP (`python -m helios.mcp.semantic` / `helios.mcp.warehouse`), declared in `.mcp.json`/`mcp_servers.yaml`. Two funnel-step metrics (`add_shipping_info_sessions`, `add_payment_info_sessions`) were added to the registry to make the full funnel query governable. Tested: `tests/test_semantic.py`, `tests/test_mcp_semantic.py`, `tests/test_warehouse.py` (fake BigQuery client — budget + reconcile + rewired `load_weekly`).

### Not started (the full mesh, per the Bible)
The other 4 MCP servers (semantic/warehouse/experiment/report) · the 7-agent plan-execute-critique SDK orchestration · memory/`report-mcp` (`save_diagnosis`/`recall_prior`) · `experiment-mcp` (power/runtime/design) · the scheduled **autonomous run** (the product's heartbeat — currently the dashboard is the entry point). These are the **v2** scope per `docs/planning/LEAN_SCOPE.md`.

### Live commands (verified)
```powershell
python diagnose.py                  # templated brief from fct_daily_funnel (needs ADC + dbt build)
python eval_labeled.py              # offline 50-scenario benchmark + CI gate check (no BigQuery)
python eval_run.py                  # 8-scenario benchmark against real marts
python synth_run.py                 # load synthetic helios_live data
python -m helios.run                # autonomous run: dated Decision Brief (synthetic source; --source bigquery for marts)
python -m helios.mcp.stats          # stats-mcp stdio server (Claude Code auto-launches via .mcp.json)
pytest tests/ -q                    # decompose golden + both eval harnesses + critic + stats-mcp
streamlit run app.py                # the dashboard
```

**Next (v2):** P0 (heartbeat), P1 (governed data path; `WEEKLY_SQL` deleted), P2 (memory + suppression), and P3 (powered experiments) have landed — **five live MCP servers** (stats, semantic, warehouse, report, experiment), and the whole pipeline is verified on real GA4. Remaining, in priority order: **P4** the full 7-agent plan-execute-critique loop (promote the single brief + the Critic into Orchestrator/Monitor/.../Critic with per-agent tool allow-lists), **P5** depth/breadth (more stats-mcp tools — forecast/cohort/rfm — 49-metric coverage, forecast-based anomaly detection instead of biggest-move). Keep the labeled-eval gate green (≥85% top-1, 0 hallucinations) through every change.
