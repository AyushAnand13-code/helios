## Quick Reference — per-milestone cheat sheet

| M | Name | Tag | Source of truth to attach | The one test that proves it | Top hallucination risk |
|---|---|---|---|---|---|
| M0 | Foundation/toolchain | Wk1 | DBT_GUIDE §1, Bible §16–17 | `dbt debug` green | wrong IAM role / dataset location not US |
| M1 | Sources, macros, seed | Wk1 | DBT_GUIDE §2–3, §6 | macros compile; `dbt seed` | inventing `event_params` keys / a 2nd channel macro |
| M2 | Staging | Wk1 | DBT_GUIDE §3 | `dbt build --select staging` | hallucinated raw GA4 columns |
| **M3** | **Sessionization + funnel (KEYSTONE)** | **Wk1** | DBT_GUIDE §4, DATA_MODEL §5 | **monotonicity + `session_key` uniqueness (golden, first)** | `did_*` vs `reached_*`; `traffic_source` as session source; wrong `session_key` |
| M4 | Marts | Wk1 | DBT_GUIDE §5, DATA_MODEL §3–8 | `revenue_reconciles` to the cent; channels = 10 | hallucinated columns; no `transaction_id` dedup |
| M5 | Semantic layer live | Wk1 | `semantic_layer.yaml` (exists), METRIC_GOVERNANCE_GUIDE | `validate_semantic.py` → 0 dangling refs | inventing metrics; wrong registry filename |
| M6 | semantic-mcp + warehouse-mcp | Wk2 | MCP_ARCHITECTURE §6.1–6.2, §9 | `build_query→dry_run→run_query→reconcile` round-trip; budget gate | the LLM hand-writing SQL |
| M6b | stats / experiment / report MCP | Wk2¹ | MCP_ARCHITECTURE §6.3–6.5, §9 | `decompose_change` golden test | computing stats in prose |
| M7 | Minimal loop (LEAN = 1 brief) | Wk2 | AGENT_ARCHITECTURE §4, §6, §13 | every brief figure traces to a tool output | the LLM inventing/recomputing numbers |
| M8 | Memory | v2 | Bible §22 | `save_diagnosis`→`recall_prior` | — |
| M9 | Full 7-agent loop | v2 | AGENT_ARCHITECTURE §5–§10 | FSM routing | — |
| M10 | Eval harness (LEAN = 6–10, local) | Wk2 | Bible §20, `scenarios.yaml` (exists) | Helios beats the naive baseline | over-claiming *causal* accuracy; an LLM-graded scorer |
| M11 | Autonomy & depth | v2 | Bible §23.3 | scheduled run | autonomy theater on a frozen dataset |
| M12 | Productionization/frontier | v2 | Bible §23.4–5 | — | — |

¹ M6b in v1 = build only the **one** server you chose (semantic *or* stats); the rest are v2.

## The golden rules (tape these to your monitor)

1. **`CLAUDE.md` at the root is your hallucination firewall** — never code without it loaded.
2. **No file without its source-of-truth doc section + the real upstream files attached.**
3. **Plan mode before any multi-file milestone.**
4. **Test-first** — and make Claude *run* the test and show you the output (don't trust, verify).
5. **The machine catches hallucinations** — `compile` + `dry_run` + `test` before you accept anything.
6. **`/clear` between milestones.**
7. **Numbers come from tools, not the LLM** (M7+) — the model narrates; `stats-mcp` computes.
8. **Spend LLM budget only on the brief** — build the deterministic layers with Claude Code.
9. **If Claude invents a name, that's a defect** — reject it, attach the registry, regenerate.

## The honesty discipline (it's also a hallucination guard)

When Claude writes the M7 brief or the M10 eval writeup, make it state plainly what is *measured* vs *assumed*: the decomposition shows *where* a metric moved (attribution), not *why* (causation); the eval proves controlled-attribution accuracy vs a baseline, not real-world causal accuracy. Forcing this honesty prevents the model from generating confident causal stories the data can't support — the exact failure the red-team flagged.
