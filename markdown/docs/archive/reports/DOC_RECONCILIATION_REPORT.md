# Helios — Documentation Reconciliation Report

**Status: COMPLETE ✅** · 2026-06-03 · Scope: consistency corrections only (no redesign; no architecture/requirements/metric-definition changes). Brought all **live** documentation in line with the current repository state after the restructure.

## 1. What was corrected (four categories)

| Category | From → To | Why |
|---|---|---|
| **Registry filename** | `models/semantic/semantic_models.yml` → `models/semantic/semantic_layer.yaml` | The live registry is the v2 file; the v1 is archived in `docs/archive/superseded/`. |
| **Metric count** | `28 metrics / 16 dims` → `47 metrics / 19 dims` | The current registry has 47 metrics / 19 dimensions. |
| **Scenario count** | `34 scenarios` → `50 scenarios` (incl. the Bible §20.3 bucket table → 10/10/6/6/6/6/6) | The benchmark in `eval/scenarios/` has 50 labeled scenarios. |
| **Doc paths** | `docs/<DOC>.md` → `docs/architecture|planning|strategy/<DOC>.md` (and the repo-layout trees) | Docs moved into subfolders during the restructure. |

## 2. Files changed (11 files · ~123 corrections)

| File | Corrections |
|---|---|
| `CLAUDE.md` | 7 — §2 source-of-truth paths; §5 registry pointer; §6 repo-layout block; §7 status note + path + `34→50`; §8 keystone registry; §10 status section. |
| `docs/architecture/HELIOS_PROJECT_BIBLE.md` | 7 — registry filename ×2 (§16.1 tree, §18.10 config); scenario count ×5 (§20.3 count + bucket table, §20.5 baseline, §20.6 harness, §20.8 CI, §20.9 results). |
| `docs/architecture/MCP_ARCHITECTURE.md` | 3 — registry path (§3 config note, §10 `mcp_servers.yaml`, §6.2 startup load). |
| `docs/architecture/AGENT_ARCHITECTURE.md` | 1 — "reads with" registry reference. |
| `docs/architecture/METRIC_DEPENDENCY_GRAPH.md` | 1 — companion registry reference. |
| `docs/architecture/METRIC_GOVERNANCE_GUIDE.md` | 4 — registry ref ×2 (header §0, footer); scenario count ×2 (§ eval gate, § benchmark). |
| `docs/planning/DEPENDENCY_MAP.md` | 6 — registry ×4 (A5.1 row, DAG node, importance #1, guardrail); scenario count ×2 (A10.3, A11.1). |
| `docs/planning/DEVELOPMENT_PLAN.md` | 6 — registry filename + count (status table); `/new-metric` cmd; doc paths ×4 (status table); scenario count ×2 (WP-10.1, CI). |
| `docs/strategy/CLAUDE_CODE_WORKFLOW.md` | 52 — `@docs/<doc>.md` attach-path prefixes ×50; the two M0-stub lines that wrongly set the registry to `semantic_models.yml`. |
| `docs/strategy/INTERVIEW_GUIDE.md` | 35 — registry filename ×22; metric count ×11; scenario count ×2. |
| `README.md` | 1 — §3 folder tree rebuilt to the current structure (the restructure banner was already added during migration). |

## 3. Intentionally NOT changed (with rationale)

- **`docs/archive/**` (62 files)** — frozen historical build fragments; never edited.
- **`RED_TEAM_REVIEW.md`** — a point-in-time assessment. It *quotes* the claims it attacked ("ships **34 scenarios**", "definitions live only in `semantic_models.yml`"). Rewriting those quotes would falsify the record. **The drifts it flagged are now resolved** by this pass.
- **"Use `semantic_layer.yaml` NOT `semantic_models.yml`" build-warnings** in `IMPLEMENTATION_PLAYBOOK.md` (5) and `CLAUDE_CODE_WORKFLOW.md` (7) — correct guidance; mentioning the retired name is the point. Kept.
- **`DEPENDENCY_MAP.md` guardrail note** — now reads "the retired v1 `semantic_models.yml` is archived in `docs/archive/superseded/`" — accurate, kept.
- **`MIGRATION_REPORT.md` / `REPO_RESTRUCTURE_PLAN.md`** — correctly cite the archived file as the archived file; unchanged.
- **`README.md` §4+ descriptive manifest** — the §3 tree was updated and a banner flags the lower sections as pre-restructure; the descriptive file-by-file prose was left (no operative impact).
- **No metric definitions, requirements, or architecture were touched** — only names, paths, and counts.

## 4. Verification (cross-references resolve)

| Check | Result |
|---|---|
| Stale `semantic_models.yml` as the **live** registry, in `docs/architecture/` | **0** ✅ |
| Stale `semantic_models.yml` remaining in live docs | 18 — **all intentional** (the build-warnings + the red-team record + the "archived" note) ✅ |
| Stale flat `docs/<DOC>.md` paths in live docs | **0** ✅ |
| Stale `34`-scenario references in live docs (excl. red-team record) | **0** ✅ |
| All 16 referenced canonical paths exist (`Test-Path`) | **16/16 True** ✅ — every doc-to-doc reference resolves to a real file. |

**Conclusion.** The live documentation set (root + `docs/architecture/` + `docs/planning/` + `docs/strategy/`) now consistently references `models/semantic/semantic_layer.yaml` (47 metrics / 19 dims), the 50-scenario benchmark, and the post-restructure folder paths. Every cross-reference resolves. The two original M5/M6 blockers the red-team and playbook flagged — the registry-filename drift and the stale paths — are closed.
