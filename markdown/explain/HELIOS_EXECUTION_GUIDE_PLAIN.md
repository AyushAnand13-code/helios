# Helios Execution Guide — In Plain English

> Plain-language companion to `HELIOS_EXECUTION_GUIDE.md`. For the exact spec, read that / its PDF.

## In one sentence
This is your daily build playbook: what to read (a little), what to ignore (a lot), the exact first task, the 4-week plan week by week, and an honest read on the project's odds.

## Why this matters to you
The architecture is ~100% done; the code is ~2% done. Your enemy is not missing information — it's drowning in it. This guide picks the four critical docs, tells you to stop reading and start writing, and lays out a realistic ~90-hour, 4-week path from empty folders to a shippable v1. It also tells you, plainly, what to never touch and what to never claim.

## The big ideas, simply
- **Read four things, then build.** `CLAUDE.md`, `LEAN_SCOPE.md`, `DBT_GUIDE.md` §1–§5, and `DATA_MODEL.md` §5 — about 2.5 hours. Everything else is opened only when a milestone needs it.
- **Three versions of the product.** **MVP** = governed mix-vs-rate diagnosis on real data, no LLM. **v1** = MVP + one MCP server + one grounded LLM brief + an honest small eval (this is what you ship). **v2** = everything fancy — postpone it all.
- **Some things are frozen.** The canonical names, the funnel/session definitions, the 10 channel groups, the decomposition math — never rewrite these. Changing one breaks everything downstream.
- **Be honest about what it is.** Helios diagnoses **WHERE** a funnel moved (which segment, mix vs rate), not **WHY**. It's a diagnosis assistant, not an autonomous always-on product. Claim the honest version — it's stronger and defensible.
- **Build velocity is the whole game.** The plans are done. Almost all the MVP code already sits in `DBT_GUIDE.md` waiting to be wired up.

## What you actually do (in order)
1. **First task (M0 only):** Create `requirements.txt` plus the three dbt config files, authenticate to BigQuery, and get `dbt debug` green plus one bounded smoke query returning rows. Copy values verbatim from `DBT_GUIDE.md` §1 — pin `location: US` and `maximum_bytes_billed: 5368709120`. Don't write a model first; you can't run it yet.
2. **Week 1 (M0–M4):** Connect dbt to BigQuery and build the tested marts — `fct_funnel`, `fct_daily_funnel`, `fct_orders`, plus `dim_date`/`dim_channels`. Write the keystone golden tests first.
3. **Week 2 (M5 + engine):** Compile the registry against real marts, build `decompose_change` (golden-tested), and run `diagnose.py` end to end — a real, priced mix-vs-rate diagnosis with no LLM.
4. **Week 3 (M6 partial + M7 lean):** Stand up one MCP server (`semantic-mcp` or `stats-mcp`) wired to Claude, and have Claude write the Decision Brief from the deterministic numbers.
5. **Week 4 (M10 lean):** Build the injector + scorer, reuse 6–10 scenarios, compare against the naive baseline, and make the whole loop run from one command.

## Easy things to get wrong
- **Over-claiming in the writeup.** The eval proves attribution accuracy, not causation. Say so.
- **Spending LLM budget too early.** Build and test the deterministic parts first; spend Claude Pro budget only on the brief.
- **GA4 struct paths.** It's `device.web_info.browser`, not `device.browser`. Wrong paths fail quietly.
- **Sessionization correctness.** It fails silently — write the golden tests before the code.
- **The registry field names.** The validator must read `metric_name`/`sql_definition`, not `name`/`sql`; you need a small adapter at load time.
- **Moving the validated registry.** Run dbt from the repo root and leave `models/semantic/semantic_layer.yaml` where it is.

## Glossary — the exact words, demystified
- **MVP / v1 / v2** — the three scope tiers; v1 is what you ship in four weeks.
- **M0–M12** — milestones in build order; weeks 1–4 cover M0 through M7 plus a lean M10.
- **Grounding rules G1–G5** — the rules that stop the LLM from writing raw SQL or computing stats in prose.
- **`decompose_change`** — the engine that splits a metric move into mix effect, rate effect, and interaction.
- **mix vs rate** — did the traffic composition change (mix) or did behavior within a segment change (rate)?
- **golden test** — a test that checks output against a hand-worked correct answer; used for silent-failure keystones.
- **naive baseline** — the dumb "largest-segment-delta" method you must beat to prove the engine works.
- **reconcile to the cent** — your computed revenue exactly matches a control query.

## When to open the real doc
Open `HELIOS_EXECUTION_GUIDE.md` (and its copy under `pdf/`) at the start of each week for the full objectives, file lists, commands, and risks — and Part 5 for the exact M0 commands. It is your week-by-week dashboard.
