# Helios — Repository Restructure Plan

**Status: PROPOSED — awaiting approval. No filesystem changes have been made.** · 2026-06-03 · Maintainer: Staff Architect

---

## 1. Repository audit

- **88 files, 14 directories.** Everything is documentation + assets; no implementation code exists yet.
- **A partial restructure is already in place** (reflected below, marked ✓ — no action needed):
  - `CLAUDE.md` is **already at the repo root**.
  - `docs/architecture/` **already exists** and holds 6 of the architecture docs.
- **Still flat in `docs/`** (need homing): `DBT_GUIDE.md`, `DEVELOPMENT_PLAN.md`, `IMPLEMENTATION_PLAYBOOK.md`, `DEPENDENCY_MAP.md`, `LEAN_SCOPE.md`, `RED_TEAM_REVIEW.md`, `INTERVIEW_GUIDE.md`, `CLAUDE_CODE_WORKFLOW.md`.
- **Generated intermediate artifacts** (assembled into final docs; to archive): `docs/sections/` (10) + six `docs/_*_sections/` folders (45) + `models/semantic/_build/` (6) = **61 files**.
- **Assets in correct homes** (keep): `models/semantic/semantic_layer.yaml` (canonical v2) and `eval/scenarios/` (9 benchmark files).
- **Two flagged items needing a decision:** `PROJECT_STRUCTURE.md` (root, no target home) and `models/semantic/semantic_models.yml` (the **retired v1** registry — a superseded duplicate of `semantic_layer.yaml`).
- **Missing dirs from the target** (to create, empty): `docs/planning/`, `docs/strategy/`, `docs/archive/`, `eval/benchmark_results/`, `dbt/`, `mcp/`, `agents/`, `backend/`, `frontend/`, `tests/`, `scripts/`, `notebooks/`, plus root `README.md`.

## 2. Migration plan & policies

- **No deletions.** Every file is moved or kept. Generated intermediates are **archived** (moved to `docs/archive/`), never deleted — honoring "preserve all content."
- **Preserve content; relocate only.** Moves use `Move-Item` (these files are untracked in git; no history to preserve). Empty future dirs get a `.gitkeep`.
- **Archive folders are renamed for clarity** (strip the `_*_sections` temp naming → descriptive names), with a one-line `README.md` dropped in each noting which final doc it was assembled into.
- **Sequencing on approval:** (1) create the new empty dirs; (2) move loose `docs/` files into `planning/`/`strategy/`/`architecture/`; (3) move the intermediate folders into `docs/archive/`; (4) resolve the two decisions; (5) verify counts (88 files still present); (6) update `README.md`'s tree section to match the new layout.

## 3. File movement table

### Already correct — NO ACTION (8 items)
| Current path | Status |
|---|---|
| `CLAUDE.md` | ✓ at root (special rule already satisfied) |
| `docs/architecture/HELIOS_PROJECT_BIBLE.md` | ✓ |
| `docs/architecture/DATA_MODEL.md` | ✓ |
| `docs/architecture/MCP_ARCHITECTURE.md` | ✓ |
| `docs/architecture/AGENT_ARCHITECTURE.md` | ✓ |
| `docs/architecture/METRIC_DEPENDENCY_GRAPH.md` | ✓ |
| `docs/architecture/METRIC_GOVERNANCE_GUIDE.md` | ✓ |
| `models/semantic/semantic_layer.yaml` | ✓ canonical v2 registry — keep |

### Move → `docs/architecture/`
| Current | New | Reason |
|---|---|---|
| `docs/DBT_GUIDE.md` | `docs/architecture/DBT_GUIDE.md` | Analytics-engineering architecture spec; belongs with the other engineering specs (not in your special-rule list, but architectural by content). |

### Move → `docs/planning/` (create)
| Current | New | Reason |
|---|---|---|
| `docs/DEVELOPMENT_PLAN.md` | `docs/planning/DEVELOPMENT_PLAN.md` | Special rule. |
| `docs/IMPLEMENTATION_PLAYBOOK.md` | `docs/planning/IMPLEMENTATION_PLAYBOOK.md` | Special rule. |
| `docs/DEPENDENCY_MAP.md` | `docs/planning/DEPENDENCY_MAP.md` | Special rule. |
| `docs/LEAN_SCOPE.md` | `docs/planning/LEAN_SCOPE.md` | Special rule. |

### Move → `docs/strategy/` (create)
| Current | New | Reason |
|---|---|---|
| `docs/RED_TEAM_REVIEW.md` | `docs/strategy/RED_TEAM_REVIEW.md` | Special rule. |
| `docs/INTERVIEW_GUIDE.md` | `docs/strategy/INTERVIEW_GUIDE.md` | Special rule. |
| `docs/CLAUDE_CODE_WORKFLOW.md` | `docs/strategy/CLAUDE_CODE_WORKFLOW.md` | Special rule. |

### Move → `docs/archive/` (create) — generated intermediate artifacts (61 files; folders move whole)
| Current folder (files) | New | Reason |
|---|---|---|
| `docs/sections/` (10) | `docs/archive/bible-sections/` | Source fragments assembled into `HELIOS_PROJECT_BIBLE.md`. |
| `docs/_interview_sections/` (15) | `docs/archive/interview-sections/` | Fragments assembled into `INTERVIEW_GUIDE.md`. |
| `docs/_dbt_sections/` (7) | `docs/archive/dbt-guide-sections/` | Fragments assembled into `DBT_GUIDE.md`. |
| `docs/_datamodel_sections/` (4) | `docs/archive/data-model-sections/` | Fragments assembled into `DATA_MODEL.md`. |
| `docs/_playbook_sections/` (7) | `docs/archive/playbook-sections/` | Fragments assembled into `IMPLEMENTATION_PLAYBOOK.md`. |
| `docs/_redteam_sections/` (5) | `docs/archive/red-team-sections/` | Fragments assembled into `RED_TEAM_REVIEW.md`. |
| `docs/_ccworkflow_sections/` (7) | `docs/archive/claude-code-workflow-sections/` | Fragments assembled into `CLAUDE_CODE_WORKFLOW.md`. |
| `models/semantic/_build/` (6) | `docs/archive/semantic-layer-build/` | Fragments merged into `semantic_layer.yaml`. |

### Keep in place — NO ACTION
| Current | Reason |
|---|---|
| `eval/scenarios/scenarios.yaml` | Benchmark asset — keep (special rule). |
| `eval/scenarios/01..07_*.yaml` (7) | Per-bucket benchmark sources — keep. |
| `eval/scenarios/_VALIDATION.md` | Benchmark validation report — keep. |

### Decisions required (flagged — see §5)
| Current | Proposed new (recommended) | Reason |
|---|---|---|
| `PROJECT_STRUCTURE.md` (root) | `README.md` (root) | It already *is* a project overview; root README is the conventional entry point. Its tree section would be updated post-migration. |
| `models/semantic/semantic_models.yml` | `docs/archive/superseded/semantic_models.yml` | **Duplicate/superseded:** the retired v1 (28 metrics, short-key schema), replaced by `semantic_layer.yaml` (v2, 47 metrics). Two registry files in one folder is the exact "future confusion" to avoid. |

### Create (empty, `.gitkeep`) — future implementation code + the target scaffold
`docs/planning/`, `docs/strategy/`, `docs/archive/`, `eval/benchmark_results/`, `dbt/`, `mcp/`, `agents/`, `backend/`, `frontend/`, `tests/`, `scripts/`, `notebooks/`.

## 4. Final folder tree (target, populated)

```text
helios/
├── README.md                          # from PROJECT_STRUCTURE.md (tree updated)   [DECISION 1]
├── CLAUDE.md                           # ✓ already at root
├── REPO_RESTRUCTURE_PLAN.md            # this doc (archive after migration)
├── docs/
│   ├── architecture/
│   │   ├── HELIOS_PROJECT_BIBLE.md     # ✓
│   │   ├── DATA_MODEL.md               # ✓
│   │   ├── DBT_GUIDE.md                # ← moved from docs/
│   │   ├── MCP_ARCHITECTURE.md         # ✓
│   │   ├── AGENT_ARCHITECTURE.md       # ✓
│   │   ├── METRIC_DEPENDENCY_GRAPH.md  # ✓
│   │   └── METRIC_GOVERNANCE_GUIDE.md  # ✓
│   ├── planning/
│   │   ├── DEVELOPMENT_PLAN.md
│   │   ├── IMPLEMENTATION_PLAYBOOK.md
│   │   ├── DEPENDENCY_MAP.md
│   │   └── LEAN_SCOPE.md
│   ├── strategy/
│   │   ├── RED_TEAM_REVIEW.md
│   │   ├── INTERVIEW_GUIDE.md
│   │   └── CLAUDE_CODE_WORKFLOW.md
│   └── archive/
│       ├── bible-sections/             (10)
│       ├── interview-sections/         (15)
│       ├── dbt-guide-sections/         (7)
│       ├── data-model-sections/        (4)
│       ├── playbook-sections/          (7)
│       ├── red-team-sections/          (5)
│       ├── claude-code-workflow-sections/ (7)
│       ├── semantic-layer-build/       (6)
│       └── superseded/
│           └── semantic_models.yml     # v1 retired   [DECISION 2]
├── models/
│   └── semantic/
│       └── semantic_layer.yaml         # ✓ canonical v2
├── eval/
│   ├── scenarios/                      # scenarios.yaml + 01–07 + _VALIDATION.md (✓)
│   └── benchmark_results/              # new (empty .gitkeep)
├── dbt/            # new (empty) — future dbt project
├── mcp/            # new (empty) — future MCP servers
├── agents/         # new (empty) — future agent code
├── backend/        # new (empty)
├── frontend/       # new (empty)
├── tests/          # new (empty)
├── scripts/        # new (empty)
└── notebooks/      # new (empty)
```

## 5. Decisions requiring your input

- **Decision 1 — `PROJECT_STRUCTURE.md`:** rename → `README.md` (recommended), keep as-is at root, or archive it?
- **Decision 2 — `semantic_models.yml` (retired v1):** archive to `docs/archive/superseded/` (recommended), or keep in `models/semantic/` with a deprecation banner? *(Note: it's still referenced by the stale registry-filename pointers in `CLAUDE.md` and `MCP_ARCHITECTURE.md` — archiving it makes the canonical `semantic_layer.yaml` unambiguous.)*

## 6. Verification (run after execution)
- Re-count: **88 files** still present (61 in `docs/archive/`, the rest relocated). 0 deletions.
- Spot-check each moved doc opens at its new path; archive subfolders carry a one-line provenance `README.md`.

---

> **Nothing will be moved until you approve.** Reply with **"approve"** (I'll proceed with the recommended resolutions for Decisions 1 & 2), or tell me how to adjust.
