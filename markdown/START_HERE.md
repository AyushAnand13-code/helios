# START HERE — Helios

**The single front door.** Read this once and you'll never feel lost again. It tells you what every folder/file is for, the handful you actually open, what to ignore, and your 4-week targets. Everything else is indexed below.

---

## 1. The mental model (internalize this and the mess disappears)

- The repo has **two layers**: **(A) the plan/spec** — ~25 documents, **100% done** — and **(B) the code** — the empty `dbt/`, `mcp/`, `agents/`… folders, **~0% done**. **Your entire job is turning A into B.**
- **You do not read everything.** You read **5 docs once**, keep **~6 open as reference**, and **ignore the rest** until a milestone needs them.
- **One rule above all:** the docs are the source of truth — you **copy/adapt** code from them, you never invent it. (That's also what makes building on Claude Pro affordable.)
- **Two front-door docs:** *this* `START_HERE.md` is the **map + week plan**; `HELIOS_EXECUTION_GUIDE.md` is the **detailed execution playbook** (first task, readiness, probability). Use this to orient, that to execute.

---

## 2. Folder map — what each folder is FOR

```
helios/
├─ START_HERE.md ........... you are here (the map)
├─ HELIOS_EXECUTION_GUIDE.md  the execution playbook (open daily)
├─ CLAUDE.md ............... auto-loads into Claude Code; the rules + canonical names
├─ README.md .............. external-context manifest (skim once, then ignore)
├─ docs/
│  ├─ architecture/ ....... WHAT the system is — the design + the code to copy
│  ├─ planning/ ........... HOW & WHEN to build it — milestones, build order, playbook, scope
│  ├─ strategy/ ........... meta — critique, interview prep, how to drive Claude
│  └─ archive/ ............ frozen build scraps — IGNORE entirely
├─ models/semantic/ ....... semantic_layer.yaml — the live metric registry (reference)
├─ eval/scenarios/ ........ the 50-scenario benchmark (you use ~6–10 in Week 4)
└─ dbt/ mcp/ agents/ backend/ frontend/ tests/ scripts/ notebooks/
                            EMPTY — this is where YOUR code goes
```

---

## 3. The ONLY files you keep open while building

Pin these. Everything else is consulted occasionally or never.

| File | Role | How you use it |
|---|---|---|
| `CLAUDE.md` | The rules | Auto-loads every Claude Code session — you don't open it, it's just *on*. |
| `HELIOS_EXECUTION_GUIDE.md` | Your dashboard | The 4-week plan + the exact first task (Part 5). |
| `docs/planning/IMPLEMENTATION_PLAYBOOK.md` | Per-milestone manual | Open the section for the milestone you're on: files · commands · tests · gotchas. |
| `docs/architecture/DBT_GUIDE.md` | The dbt code | Copy the SQL/config for M0–M4 (§1–§5). |
| `docs/architecture/DATA_MODEL.md` §5 | The keystone | Sessionization + funnel flags (the part that fails silently). |
| `docs/architecture/MCP_ARCHITECTURE.md` §6/§9 | The MCP server | Week 3 — copy the server skeleton. |
| `models/semantic/semantic_layer.yaml` | The registry | Look up a metric's definition when you need it (never read whole). |
| `docs/planning/DEVELOPMENT_PLAN.md` §12 | The tracker | Tick off each milestone as it goes green. |

---

## 4. Full file index (one line each)

**`docs/architecture/` — what the system is**
- `HELIOS_PROJECT_BIBLE.md` — the 233 KB master spec. **Never read whole**; jump to a numbered § only if a smaller doc doesn't answer you.
- `DATA_MODEL.md` — every table's grain/PK/FK + the ER diagram. **§5 is the keystone** (sessionization/funnel).
- `DBT_GUIDE.md` — **the literal dbt code** to copy (config, staging, marts, tests). Your Week 1–2 workhorse.
- `MCP_ARCHITECTURE.md` — the 5 MCP servers; **§9 has the Python skeletons** to copy in Week 3.
- `AGENT_ARCHITECTURE.md` — the 7-agent design. For the lean build you need **only §6.7** (the brief); the rest is v2.
- `METRIC_DEPENDENCY_GRAPH.md` — metric trees + identities (RPS = conv × AOV). Consult when coding the decomposition.
- `METRIC_GOVERNANCE_GUIDE.md` — how the registry is validated/versioned. Consult at M5.

**`docs/planning/` — how & when to build**
- `IMPLEMENTATION_PLAYBOOK.md` — **the build manual**: M0–M12, each with files/commands/tests/success/mistakes.
- `DEVELOPMENT_PLAN.md` — work packages + the **milestone tracker** + exit gates.
- `DEPENDENCY_MAP.md` — what-depends-on-what + the critical path (consult if unsure what's next).
- `LEAN_SCOPE.md` — **what to build vs cut** (MVP/v1/v2). Read once, early.

**`docs/strategy/` — meta**
- `RED_TEAM_REVIEW.md` — the honest critique. Read once so you avoid the traps (don't claim "autonomous"/"why").
- `CLAUDE_CODE_WORKFLOW.md` — how to drive Claude Code per milestone (prompts, anti-hallucination). Reference.
- `INTERVIEW_GUIDE.md` — job-hunt prep. **Ignore until you're interviewing.**

**Root — housekeeping (ignore while building)**
- `MIGRATION_REPORT.md`, `REPO_RESTRUCTURE_PLAN.md`, `DOC_RECONCILIATION_REPORT.md` — records of repo reorg. No build value.
- `CLAUDE.pdf`, `Helios_on_Claude_Pro.pdf` — shareable copies only.

---

## 5. Your 4-week targets (≈20–25 hrs/week)

| Week | Milestones | Target (the deliverable) | Done when… |
|---|---|---|---|
| **1 — Data spine** | M0–M4 | Governed dbt marts on real GA4 (`fct_funnel`, `fct_daily_funnel`, `fct_orders`, dims), tested | `dbt build` green · revenue **reconciles to the cent** · funnel is **monotonic** · channels = exactly 10 |
| **2 — MVP** | M5 + decomposition | Registry live + the mix-vs-rate engine + a templated diagnosis (no LLM) | `validate_semantic.py` → 0 dangling refs · `decompose_change` **golden test** passes · one funnel move diagnosed + priced end-to-end |
| **3 — v1 core** | M6 (one server) + M7 (brief) | One MCP server wired to Claude + a **grounded** Decision Brief | `build_query→dry_run→run_query` round-trips · every number in the brief traces to a tool output · **0 hallucinated columns** |
| **4 — v1 shipped** | M10 (honest eval) + writeup | 6–10 labeled scenarios + naive baseline + case study | Helios **beats the baseline** · honest accuracy number with caveats · the whole loop runs from **one command** |

**The cut line (do NOT build in these 4 weeks):** the 7-agent fleet, the Critic loop, memory/vector store, the scheduler/autonomy, `experiment-mcp`, cohorts/retention/RFM/forecasting, the other 4 MCP servers, the full 50-scenario CI gate, the frontend. (Per `LEAN_SCOPE.md` + `RED_TEAM_REVIEW.md`.)

---

## 6. Your daily build loop (the rhythm)

1. Open `IMPLEMENTATION_PLAYBOOK.md` at your current milestone; check the exit gate in `DEVELOPMENT_PLAN.md` §12.
2. In Claude Code: paste the milestone prompt (`HELIOS_EXECUTION_GUIDE.md` has it) + **attach the exact `DBT_GUIDE`/`MCP_ARCHITECTURE` section** named in the playbook.
3. Have Claude **plan first**, then **write the test**, then the code. **You** run `dbt build`/`pytest` and paste the real output.
4. Pass the exit gate → **tick the tracker** → `git commit` → `/clear` → next milestone.
5. Hit a Claude Pro limit? Switch to token-free work (run dbt, write a test, set up the next piece) until it resets.

---

## 7. Where you are right now → the next move

You are **pre-M0** (nothing built yet). **Next action:** `HELIOS_EXECUTION_GUIDE.md` **Part 5** — create the 4 dbt config files from `DBT_GUIDE.md §1`, authenticate to BigQuery, and get `dbt debug` green + one smoke query returning rows. That's tonight's whole job. Then start Week 1.

> If you only remember one sentence: **open the playbook at your milestone, copy the code from the architecture doc it cites, test it, tick the tracker, repeat.** Four weeks of that = Helios v1.
