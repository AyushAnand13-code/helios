# Helios — Project Structure & Manifest

> 🧭 **New here / want to understand & defend the project? → [`docs/onboarding/`](docs/onboarding/README.md)**
> Plain-English, ground-up explainers (no dbt/BigQuery/MCP background assumed): what Helios is,
> the core mix-vs-rate idea, the data, the architecture, a dashboard walkthrough, a glossary, and
> an interview playbook.

> 🚀 **Live demo → https://helios-5be8rdzgr7vprmfhxqsj4k.streamlit.app/**
> An interactive growth-diagnosis dashboard on real GA4 data: it finds the biggest
> week-over-week conversion move, separates **mix-shift from rate-change**, tests
> significance, and prices it in **dollars of revenue-at-risk** — all from governed dbt
> marts + a deterministic stats engine (no LLM, no hand-written SQL).
> Run it locally with `streamlit run app.py`. *(Free tier: first load may take ~30s to wake.)*

> **Repository restructured 2026-06-03** into `docs/{architecture,planning,strategy,archive}/`, `models/semantic/`, `eval/`, and (empty) implementation dirs (`dbt/ mcp/ agents/ backend/ frontend/ tests/ scripts/ notebooks/`). The authoritative current layout is in `MIGRATION_REPORT.md` and `REPO_RESTRUCTURE_PLAN.md`. The detailed sections below predate the restructure — still accurate on *what Helios is*, but file paths have moved.

> Paste this whole file into ChatGPT (or any LLM) to give it complete context on what has been built.

---

## 0. One-paragraph summary (read first)

**Helios is an "Autonomous Growth Diagnosis Engine"** — an always-on AI growth analyst that diagnoses **why** an e-commerce funnel moved, separates **mix-shift** (traffic composition changed) from **rate-change** (in-segment behavior changed), quantifies the movement as **revenue-at-risk in dollars**, prescribes a **prioritized, statistically-defensible experiment backlog**, and ships an executive **Decision Brief** — all grounded in **governed SQL it never hand-writes**, and graded by an **offline labeled benchmark**. It is deliberately **not** a dashboard and **not** a SQL chatbot; it runs autonomously. It is built on the public **Google Merchandise Store GA4 dataset** (`bigquery-public-data.ga4_obfuscated_sample_ecommerce`, Nov 2020–Jan 2021). Stack: **BigQuery + dbt + Python MCP servers (scipy/statsmodels/prophet) + Claude Agent SDK + Model Context Protocol + GitHub Actions CI**.

## 1. Current stage (important context)

This repo is currently a **complete specification + governed semantic layer + evaluation benchmark + interview prep** — **not yet running code**. Everything is *designed in depth*; implementation (the dbt models, the 5 MCP servers, the 7 agents, the eval harness) is fully planned in the docs but not yet written. So when reasoning about it, treat it as a **design/spec/benchmark project**, not a deployed system.

## 2. The architecture in 6 lines

- **5 MCP servers** — `warehouse-mcp` (the only BigQuery client; dry-run→run-query byte-budget gate; reconcile), `semantic-mcp` (the ONLY path to SQL; composes governed SQL from the metric registry → 0 hallucinated columns), `stats-mcp` (the ONLY path to math; the mix/rate decomposition, significance, forecasting), `experiment-mcp` (power/sample-size/test-design), `report-mcp` (Decision Brief + memory).
- **7 agents on a deterministic state machine** (the LLM composes tool calls, never controls flow): Orchestrator → Monitor → Decompose → Diagnose → Critic → Prescribe → Narrator.
- **Semantic layer** — one governed YAML registry of every metric/dimension; the single source of truth.
- **Memory** — diagnosis history, suppression list, seasonality/launch calendars, action-tracking (did-the-fix-work loop).
- **Evaluation** — synthetic anomalies injected into a frozen GA4 copy; 50 labeled scenarios; target **≥85% root-cause accuracy vs ≤45% naive baseline**, 0 hallucinated columns, <5 min/run, ≤5 GiB/run.
- **Technical centerpiece** — mix-vs-rate decomposition: `ΔR = mix(Σ Δwᵢ·rᵢ) + rate(Σ wᵢ·Δrᵢ) + interaction(Σ Δwᵢ·Δrᵢ)`, which dissolves Simpson's paradox.

## 3. Folder tree

```
helios/
├─ README.md · CLAUDE.md · .gitignore · MIGRATION_REPORT.md · REPO_RESTRUCTURE_PLAN.md
├─ docs/
│  ├─ architecture/  HELIOS_PROJECT_BIBLE · DATA_MODEL · DBT_GUIDE · MCP_ARCHITECTURE · AGENT_ARCHITECTURE · METRIC_DEPENDENCY_GRAPH · METRIC_GOVERNANCE_GUIDE
│  ├─ planning/      DEPENDENCY_MAP · DEVELOPMENT_PLAN · IMPLEMENTATION_PLAYBOOK · LEAN_SCOPE
│  ├─ strategy/      CLAUDE_CODE_WORKFLOW · INTERVIEW_GUIDE · RED_TEAM_REVIEW
│  └─ archive/       (frozen build fragments: bible/interview/dbt-guide/data-model/playbook/red-team/claude-code-workflow-sections, semantic-layer-build, superseded/semantic_models.yml)
├─ models/semantic/ semantic_layer.yaml   (PRODUCTION registry — 47 metrics, 19 dims, 7 entities)
├─ eval/
│  ├─ scenarios/     scenarios.yaml + 01–07_*.yaml + _VALIDATION.md   (50-scenario benchmark)
│  └─ benchmark_results/
└─ dbt/ · mcp/ · agents/ · backend/ · frontend/ · tests/ · scripts/ · notebooks/   (implementation code — empty until M0+; each has a placeholder README)
```

## 4. File-by-file (what each is and why it matters)

### Documentation (`docs/`)
| File | What it is | Why it matters |
|---|---|---|
| `HELIOS_PROJECT_BIBLE.md` | The master spec — 25 sections: vision, business problem, personas, functional/non-functional requirements, data model, event model, funnel/revenue/attribution/metric definitions, semantic layer, analytics-engineering & dbt & BigQuery architecture, MCP architecture, agent architecture, memory, evaluation, experimentation, roadmap, interview & resume narratives. | The authoritative, rebuild-from-scratch reference. Everything else derives from it. |
| `CLAUDE.md` | Operating manual for any AI agent working on the repo: canonical metric/dimension/agent names, the grounding rules (G1–G5), dbt conventions, commands, the keystones that fail silently. | The continuity anchor — keeps every coding session consistent. |
| `DEPENDENCY_MAP.md` | Every artifact (T0–T13), what depends on what, the recommended generation order (milestones M0–M12), the keystones, and the critical path. | The build-time blueprint. |
| `DEVELOPMENT_PLAN.md` | The execution plan: work packages, the Claude Code workflow per activity, test/exit gates, a living milestone tracker, risk register. | How the project actually gets built, step by step. |
| `MCP_ARCHITECTURE.md` | Implementation spec for the 5 MCP servers: every tool's typed I/O, the guardrail chain, transport/auth, the error taxonomy, the per-agent tool allow-list, code skeletons. | Build spec for the tool layer. |
| `AGENT_ARCHITECTURE.md` | Implementation spec for the 7 agents: the deterministic FSM, the typed "Finding" hand-off envelope, the Critic refutation loop, the hypothesis-tree root-cause search, the revenue-at-risk formula, the tunable constants. | Build spec for the agent layer. |
| `METRIC_DEPENDENCY_GRAPH.md` | Dependency trees for every metric + RCA decomposition paths + the key identities (e.g. revenue_per_session = session_conversion_rate × aov). | How metrics relate; drives root-cause analysis. |
| `METRIC_GOVERNANCE_GUIDE.md` | Governance for the semantic layer: the single-source-of-truth rule, the field-schema contract, versioning, how each agent consumes it, the validation/CI pipeline, the guardrail philosophy. | How the metric layer is owned and kept correct. |
| `INTERVIEW_GUIDE.md` | 13 sections: project story, 5 elevator pitches, ~250 interview Q&A across Product/Growth/Data Analytics + Analytics Engineering + AI Engineering, system design, skeptic questions, resume bullets, STAR stories, founder round, top-1% prep — plus the "Helios Fact Sheet" cheat card. | How to present the project in interviews / placement. |
| `sections/00-09…md` | The 10 thematic source fragments the Bible was assembled from. | Source-of-truth fragments; the Bible is their concatenation. |

### Semantic layer (`models/semantic/`)
| File | What it is | Why it matters |
|---|---|---|
| `semantic_layer.yaml` | **The production registry.** 47 metrics (34 named + 13 supporting) across revenue/traffic/funnel/conversion/retention/acquisition/product, 19 dimensions, 7 entities, 4 time grains. Each metric carries: business definition, SQL, aggregation, grain, supported dimensions, owner, caveats, common mistakes, **guardrails** (when-not-to-use / Simpson's-paradox / attribution / segmentation), **root-cause** (upstream drivers, downstream impacts, decomposition path), **which agents use it**, validation checks, **dbt/quality/anomaly/reconciliation tests**, freshness. Referential-integrity validated (0 dangling references). | The single source of truth for all metrics; no metric may exist outside it. |
| `semantic_models.yml` | The v1 minimal registry (28 metrics, 16 dims). | Superseded by `semantic_layer.yaml`; kept for history. |

### Evaluation benchmark (`eval/scenarios/`)
| File | What it is | Why it matters |
|---|---|---|
| `scenarios.yaml` | **The benchmark** — 50 labeled e-commerce anomaly scenarios across 7 buckets (single/multi rate, single/multi mix, seasonality decoys, no-anomaly controls, data-quality artifacts). Each has the injection spec + 5 labels: anomaly, ground-truth, expected diagnosis, expected recommendation, expected revenue impact. | This is how Helios's accuracy is *proven* (≥85% vs ≤45% baseline). The trust centerpiece. |
| `01_…07_*.yaml` | The 7 per-bucket source files. | Editable sources for the benchmark. |
| `_VALIDATION.md` | The verifier's report confirming canonical-name compliance, ID/coverage integrity, windows, revenue sanity. | Proof the benchmark is well-formed. |

## 5. How the documents relate (the hierarchy)

```
HELIOS_PROJECT_BIBLE.md  (master spec — the "why" and the full design)
   │
   ├── derives →  MCP_ARCHITECTURE.md      (tool-layer build spec)
   ├── derives →  AGENT_ARCHITECTURE.md    (agent-layer build spec)
   ├── derives →  semantic_layer.yaml      (the governed metrics)  ── governed by → METRIC_GOVERNANCE_GUIDE.md
   │                                                                └── related by → METRIC_DEPENDENCY_GRAPH.md
   ├── graded by →  eval/scenarios/scenarios.yaml   (the 50-scenario benchmark)
   │
   ├── built via →  DEPENDENCY_MAP.md  +  DEVELOPMENT_PLAN.md   (what to build, in what order)
   ├── governed by →  CLAUDE.md        (operating rules for every session)
   └── pitched via →  INTERVIEW_GUIDE.md
```

## 6. Canonical vocabulary (so the LLM uses the right names)

- **Funnel:** `session_start → view_item → add_to_cart → begin_checkout → add_shipping_info → add_payment_info → purchase`
- **Session key** = `(user_pseudo_id, ga_session_id)`; funnel flags are `reached_*` (max-downstream, monotonic).
- **10 channel groups:** Direct, Organic Search, Paid Search, Display, Paid Social, Organic Social, Email, Affiliates, Referral, Other.
- **Headline numbers:** ≥85% root-cause accuracy vs ≤45% naive baseline; 0 hallucinated columns; <5 min/run; ≤5 GiB/run; 50 labeled scenarios; 47 metrics / 19 dimensions; ~250 interview questions; 25-section Bible.
- **The 3 trust pillars:** (1) governed-SQL grounding, (2) deterministic statistics, (3) adversarial verification + offline eval. Thesis: *the hard part isn't generating insights — it's making them correct and trusted.*
- **Honest limits:** the dataset is observational & ~3 months, so Helios *designs/sizes* experiments and runs quasi-experimental readbacks (not live A/Bs); LTV and cross-device identity are deferred; user metrics are cookie-grain.

## 7. Suggested intro line to paste before this file

> "Here is the full structure and design of a portfolio project called **Helios**, an autonomous AI growth-diagnosis engine built on the GA4 Google Merchandise Store dataset. It is currently fully *specified* (architecture, governed semantic layer, and a 50-scenario evaluation benchmark) but not yet *implemented in code*. Read the manifest below, then [your question]."

---

*Footnote: `CLAUDE.md` and the Bible currently sit under `docs/`; `CLAUDE.md` conventionally lives at the repo root so Claude Code auto-loads it (a trivial move). The `_build/` and `_interview_sections/` directories are intermediate scaffolding already merged into the final files and are safe to delete.*
