# Start Here — In Plain English

> Plain-language companion to `START_HERE.md`. For the exact spec, read that / its PDF.

## In one sentence
This is the map of the whole repo: it tells you which handful of files to actually open, what to ignore, and what you should have built by the end of four weeks.

## Why this matters to you
The repo has a lot of documents and almost no code. It is very easy to drown in reading and never start building. This file is the antidote: it points you at the five docs that matter, keeps six open as reference, and tells you to ignore everything else until a milestone forces you to look. Read it once and you stop feeling lost.

## The big ideas, simply
- **The repo is two layers.** Layer A is the plan and spec — about 25 documents, basically finished. Layer B is the code — empty folders like `dbt/`, `mcp/`, `agents/`. Your whole job is turning A into B.
- **You don't read everything.** Read 5 docs once, keep ~6 open as reference, ignore the rest.
- **You copy, you don't invent.** The docs already contain the code. You adapt it; you never make up new SQL or metrics. (This also keeps the Claude Pro bill low.)
- **Two front doors.** `START_HERE.md` (this) is the map and week plan. `HELIOS_EXECUTION_GUIDE.md` is the detailed daily playbook. Use this to orient, that to execute.
- **`CLAUDE.md` is always on.** It auto-loads into every Claude Code session, so the rules and canonical names are always in context. You don't open it; it's just there.

## What you actually do (in order)
1. **Tonight (pre-M0 → M0):** Go to `HELIOS_EXECUTION_GUIDE.md` Part 5. Create the four dbt config files from `DBT_GUIDE.md` §1, connect to BigQuery, and get `dbt debug` green plus one small test query returning rows. That's the whole job for tonight.
2. **Week 1 (M0–M4):** Build the dbt data tables (`fct_funnel`, `fct_daily_funnel`, `fct_orders`, plus dimension tables). Done when `dbt build` is green, revenue matches to the cent, the funnel is monotonic, and channels equal exactly 10.
3. **Week 2 (M5 + decomposition):** Turn on the metric registry and build the mix-vs-rate engine (`decompose_change`). Done when the validator finds 0 dangling refs, the golden test passes, and one funnel move is diagnosed and priced.
4. **Week 3 (M6 + M7):** Wire one MCP server to Claude and produce a grounded Decision Brief. Done when queries round-trip and every number traces to a tool output (0 hallucinated columns).
5. **Week 4 (M10 + writeup):** Run 6–10 labeled scenarios against a naive baseline. Done when Helios beats the baseline and the whole loop runs from one command.

**The daily rhythm:** open the playbook at your milestone, copy the code from the architecture doc it cites, write the test, run it yourself, paste the real output, tick the tracker, commit, `/clear`, repeat.

## Easy things to get wrong
- **Reading too much.** The number one failure mode is documentation overload. Cap reading and start coding.
- **Writing a model before M0 works.** You can't run anything until dbt talks to BigQuery. Do M0 first.
- **Building cut-line items.** The 7-agent fleet, the Critic loop, memory, the scheduler, the other 4 MCP servers, the frontend — none of these belong in the 4-week build.
- **Reading the Bible cover to cover.** It's 233 KB. Jump to a numbered section only when a smaller doc can't answer you.
- **Inventing code.** If it's not in a doc, you're probably drifting. Copy and adapt.

## Glossary — the exact words, demystified
- **M0–M12** — the 13 milestones, in build order. M0 is setup; M12 is far-future production.
- **dbt** — the tool that turns your SQL files into governed BigQuery tables.
- **marts** — the final, clean tables you build (`fct_*`, `dim_*`).
- **monotonic funnel** — each funnel step has fewer or equal sessions than the one before, so step rates never exceed 1.
- **`semantic_layer.yaml`** — the registry: the single list of approved metrics and their SQL.
- **MCP server** — a small service that gives the LLM safe, governed tools (instead of letting it write raw SQL).
- **Decision Brief** — the final output: a short report explaining a funnel move, priced in dollars.
- **hallucinated column** — a made-up table/column name; the target is zero of these.

## When to open the real doc
Open `START_HERE.md` (and its copy under `pdf/`) whenever you lose the thread of what to build next, or need the full file index. For the exact first task, jump to `HELIOS_EXECUTION_GUIDE.md` Part 5.
