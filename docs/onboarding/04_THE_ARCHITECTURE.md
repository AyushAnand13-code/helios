# 4. The architecture: how the pieces fit (plain English)

Here's the whole system end-to-end. Read the diagram, then the explanation of each piece.

```
   REAL GA4 DATA (BigQuery)
         │
         ▼
   ┌───────────┐   dbt builds clean tables, tested
   │   dbt     │──► fct_funnel, fct_daily_funnel, … (the "marts")
   └───────────┘
         │
         ▼
   ┌──────────────────────────────────────────────────────────────┐
   │  THE 5 "MCP SERVERS"  (governed tools — see below for what     │
   │  MCP means)                                                    │
   │                                                                │
   │  semantic-mcp   → writes the SQL (from the metric registry)    │
   │  warehouse-mcp  → runs the SQL on BigQuery (with a cost check) │
   │  stats-mcp      → does the math (decomposition, significance,  │
   │                   forecasting)                                 │
   │  experiment-mcp → sizes the A/B test                           │
   │  report-mcp     → remembers past findings (so it doesn't spam) │
   └──────────────────────────────────────────────────────────────┘
         │
         ▼
   ┌──────────────────────────────────────────────────────────────┐
   │  THE 7 "AGENTS" (a step-by-step pipeline with roles)          │
   │  Monitor → Decompose → Diagnose → CRITIC(gate) → Prescribe →   │
   │  Narrator → Orchestrator                                       │
   └──────────────────────────────────────────────────────────────┘
         │
         ├──► a dated DECISION BRIEF (markdown)  ← the autonomous daily output
         └──► the STREAMLIT DASHBOARD            ← a human viewer of the same thing
```

## What is "MCP"? (you haven't used it — here's the plain version)
**MCP (Model Context Protocol)** is a recent open standard (from Anthropic, 2024) for giving
an AI model a set of **tools** it can call — in a structured, safe way. A "tool" is just a
function the AI is allowed to call (like "decompose this change" or "run this query").

Why it matters here: instead of letting the AI **write SQL or do math itself** (where it might
hallucinate a number), the AI is only allowed to **call these governed tools**. The tools are
real, tested Python code. So every number in the output is a real computation, not something
the language model made up.

Think of the MCP servers as **the AI's tightly-controlled toolbox.** Each "server" is just a
small program that exposes a few tools:

| MCP server | Plain-English job | Example tools |
|---|---|---|
| **semantic-mcp** | "Write the SQL for me, from the approved metric definitions." | `build_query` |
| **warehouse-mcp** | "Run this SQL on BigQuery — but first check it won't scan too much data (cost guard)." | `dry_run`, `run_query`, `reconcile` |
| **stats-mcp** | "Do the math." (the mix/rate decomposition, significance test, forecasting) | `decompose_change`, `significance_test`, `detect_anomaly` |
| **experiment-mcp** | "Size an A/B test for this finding." | `power_analysis`, `design_experiment` |
| **report-mcp** | "Remember findings so we don't re-alert the same thing every day." | `save_diagnosis`, `recall_prior` |

> **Interview line:** *"The AI never writes SQL or computes a statistic directly — it can only
> call governed MCP tools that wrap real, tested code. That's how I guarantee zero hallucinated
> numbers: the model writes the prose, the tools produce every figure."*

## What are "the 7 agents"? (and the honest caveat)
The work is organised as a **pipeline of 7 named roles**, run in order, each allowed to use
only certain tools (an "allow-list"):

1. **Monitor** — spots the week that looks anomalous (using forecasting).
2. **Decompose** — splits the move into mix / rate / interaction.
3. **Diagnose** — runs the significance test, prices the dollar impact.
4. **Critic** — *the gate*: tries to prove the finding wrong (is it significant? does it
   reconcile? is it really a rate change or just mix? is it a data-quality glitch?). If the
   Critic rejects it, the finding is **held**, not shipped.
5. **Prescribe** — sizes the A/B test.
6. **Narrator** — writes the brief.
7. **Orchestrator** — coordinates, and decides whether to alert.

The **allow-lists are enforced**: e.g. the Narrator (which writes prose) is literally not
allowed to run a database query — if it tries, the code throws an error. That's a real
governance/safety property, and it's tested.

> **Be honest about this in interviews:** *"It's a deterministic, role-based pipeline with
> enforced per-agent tool permissions and a Critic that gates findings — not seven autonomous
> AI agents talking to each other. Promoting it to true LLM agents with the Claude Agent SDK is
> the natural next step."* Saying this makes you **more** credible, not less.

## The two outputs
- **The Decision Brief** — a short markdown report (headline, why it moved, dollar impact,
  recommended action, a sized experiment, and the Critic's verdict). The **autonomous daily
  run** (`python -m helios.run`) produces this on a schedule, and only "alerts" on genuinely
  new, material findings (it suppresses repeats and known-seasonal moves like Black Friday).
- **The dashboard** — a Streamlit web app that shows the *same* diagnosis interactively for a
  human to explore. (Walkthrough in [05_THE_DASHBOARD.md](05_THE_DASHBOARD.md).)

## The five principles (why it's "governed")
Everything above serves five rules the project never breaks:
1. **Grounding over generation** — the AI composes governed tools; it never writes raw SQL or
   computes a statistic in prose.
2. **Verify-then-trust** — every finding is attacked by the Critic before it ships.
3. **Determinism where it matters** — all the math runs in real, seeded Python, not in the
   language model.
4. **Every finding is actionable** — it must carry a significance test, a dollar impact, and a
   recommended action (that's why the experiment exists).
5. **Proactive, not reactive** — built for the scheduled daily run first; the dashboard is
   secondary.

> **Interview line (decode of the scary tagline):** the banner says *"Governed mix-vs-rate
> funnel diagnosis on real GA4 data — no LLM-written SQL, no in-prose math."* In plain words:
> *"It diagnoses the sales funnel by separating mix from rate (governed = from approved metric
> definitions), on real Google Analytics data, and the AI is never allowed to write the SQL or
> do the arithmetic itself."*

Next: **[05_THE_DASHBOARD.md](05_THE_DASHBOARD.md)** — what every box on the dashboard means.
